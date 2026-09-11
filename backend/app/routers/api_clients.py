import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import log as audit_log
from app.config import settings
from app.database import get_db
from app.dependencies import require_permission
from app.exceptions import NotFoundException
from app.models.user import User
from app.repositories import api_client as client_repo
from app.repositories import client_usage as usage_repo
from app.schemas.api_client import (
    ApiClientCreatedResponse,
    ApiClientOut,
    ApiClientUsageOut,
    CreateApiClientRequest,
    UpdateApiClientRequest,
)

router = APIRouter(prefix="/api/v1/api-clients", tags=["api-clients"])


@router.get("", dependencies=[require_permission("api_clients.manage")])
async def list_api_clients(db: AsyncSession = Depends(get_db)) -> list[ApiClientOut]:
    clients = await client_repo.list_api_clients(db)
    return [ApiClientOut.model_validate(c) for c in clients]


@router.post("", status_code=201)
async def create_api_client(
    body: CreateApiClientRequest,
    request: Request,
    actor: User = require_permission("api_clients.manage"),
    db: AsyncSession = Depends(get_db),
) -> ApiClientCreatedResponse:
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="El nombre es obligatorio.")
    if not body.scopes:
        raise HTTPException(status_code=400, detail="Selecciona al menos un scope.")

    client, secret = await client_repo.create_api_client(db, name=body.name.strip(), scopes=body.scopes)
    await audit_log(request, actor, "api_client.created", client.name, scopes=body.scopes)
    return ApiClientCreatedResponse(client=ApiClientOut.model_validate(client), secret=secret)


@router.patch("/{client_id}")
async def update_api_client(
    client_id: uuid.UUID,
    body: UpdateApiClientRequest,
    request: Request,
    actor: User = require_permission("api_clients.manage"),
    db: AsyncSession = Depends(get_db),
) -> ApiClientOut:
    client = await client_repo.get_api_client_by_id(db, client_id)
    if not client:
        raise NotFoundException()
    if body.rate_limit:
        try:
            int(body.rate_limit.split("/")[0]), int(body.rate_limit.split("/")[1])
        except (ValueError, IndexError):
            raise HTTPException(status_code=422, detail="rate_limit debe ser '<n>/<segundos>'.") from None
    if body.ocr_extractor_override and body.ocr_extractor_override not in ("none", "rules", "llm"):
        raise HTTPException(
            status_code=422, detail="ocr_extractor_override debe ser 'none', 'rules' o 'llm' (o vacío)."
        )
    client = await client_repo.update_api_client(
        db,
        client,
        rate_limit=body.rate_limit,
        monthly_page_quota=body.monthly_page_quota,
        ocr_extractor_override=body.ocr_extractor_override,
    )
    await audit_log(
        request,
        actor,
        "api_client.updated",
        client.name,
        rate_limit=body.rate_limit,
        monthly_page_quota=body.monthly_page_quota,
        ocr_extractor_override=body.ocr_extractor_override,
    )
    return ApiClientOut.model_validate(client)


@router.get("/{client_id}/usage", dependencies=[require_permission("api_clients.manage")])
async def api_client_usage(client_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> ApiClientUsageOut:
    client = await client_repo.get_api_client_by_id(db, client_id)
    if not client:
        raise NotFoundException()
    row = await usage_repo.get_month(db, client.id)
    pages = row.pages if row else 0
    quota = client.monthly_page_quota or settings.ocr_default_monthly_page_quota or None
    return ApiClientUsageOut(
        period=usage_repo.current_period(),
        pages=pages,
        requests=row.requests if row else 0,
        monthly_page_quota=quota,
        quota_remaining=max(0, quota - pages) if quota else None,
        rate_limit=client.rate_limit or settings.throttle_ocr,
    )


@router.post("/{client_id}/rotate")
async def rotate_api_client_secret(
    client_id: uuid.UUID,
    request: Request,
    actor: User = require_permission("api_clients.manage"),
    db: AsyncSession = Depends(get_db),
) -> ApiClientCreatedResponse:
    client = await client_repo.get_api_client_by_id(db, client_id)
    if not client:
        raise NotFoundException()
    secret = await client_repo.rotate_secret(db, client)
    await audit_log(request, actor, "api_client.rotated", client.name)
    return ApiClientCreatedResponse(client=ApiClientOut.model_validate(client), secret=secret)


@router.delete("/{client_id}", status_code=204)
async def delete_api_client(
    client_id: uuid.UUID,
    request: Request,
    actor: User = require_permission("api_clients.manage"),
    db: AsyncSession = Depends(get_db),
) -> None:
    client = await client_repo.get_api_client_by_id(db, client_id)
    if not client:
        raise NotFoundException()
    await client_repo.revoke_api_client(db, client)
    await audit_log(request, actor, "api_client.revoked", client.name)
