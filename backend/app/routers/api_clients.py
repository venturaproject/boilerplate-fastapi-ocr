import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.exceptions import NotFoundException
from app.repositories import api_client as client_repo
from app.schemas.api_client import (
    ApiClientCreatedResponse,
    ApiClientOut,
    CreateApiClientRequest,
)

router = APIRouter(prefix="/api/v1/api-clients", tags=["api-clients"])


@router.get("", dependencies=[require_permission("api_clients.manage")])
async def list_api_clients(db: AsyncSession = Depends(get_db)):
    clients = await client_repo.list_api_clients(db)
    return [ApiClientOut.model_validate(c) for c in clients]


@router.post("", dependencies=[require_permission("api_clients.manage")], status_code=201)
async def create_api_client(body: CreateApiClientRequest, db: AsyncSession = Depends(get_db)):
    if not body.name.strip():
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="El nombre es obligatorio.")
    if not body.scopes:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Selecciona al menos un scope.")

    client, secret = await client_repo.create_api_client(db, name=body.name.strip(), scopes=body.scopes)
    return ApiClientCreatedResponse(client=ApiClientOut.model_validate(client), secret=secret)


@router.delete("/{client_id}", dependencies=[require_permission("api_clients.manage")], status_code=204)
async def delete_api_client(client_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    client = await client_repo.get_api_client_by_id(db, client_id)
    if not client:
        raise NotFoundException()
    await client_repo.revoke_api_client(db, client)
