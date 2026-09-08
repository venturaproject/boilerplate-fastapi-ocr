from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.exceptions import ForbiddenException, UnauthorizedException
from app.models.api_client import ApiClient, ApiClientToken
from app.models.user import User
from app.services.jwt import jwt_service

# ── User auth ─────────────────────────────────────────────────────────────────


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    token = request.cookies.get("access_token")
    if not token:
        raise UnauthorizedException()

    payload = jwt_service.validate_access_token(token)
    if not payload:
        raise UnauthorizedException()

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException()

    result = await db.execute(
        select(User)
        .options(
            selectinload(User.roles).selectinload(__import__("app.models.role", fromlist=["Role"]).Role.permissions),
            selectinload(User.settings),
        )
        .where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise UnauthorizedException()

    if user.status != User.STATUS_ACTIVE:
        raise HTTPException(status_code=403, detail="Tu cuenta está desactivada")

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_permission(perm: str) -> Any:
    async def dep(user: User = Depends(get_current_user)) -> User:
        if perm not in user.permission_names:
            raise ForbiddenException()
        return user

    return Depends(dep)


# ── External API auth ────────────────────────────────────────────────────────


class ExtClientContext:
    def __init__(self, client: ApiClient, scopes: list[str]) -> None:
        self.client = client
        self.scopes = scopes

    def has_scope(self, scope: str) -> bool:
        return "*" in self.scopes or scope in self.scopes


async def get_ext_client(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ExtClientContext:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token de autorización requerido")

    raw_token = auth_header[len("Bearer ") :]
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    result = await db.execute(
        select(ApiClientToken)
        .options(selectinload(ApiClientToken.client))
        .where(
            ApiClientToken.access_token_hash == token_hash,
            ApiClientToken.access_expires_at > datetime.now(tz=UTC),
        )
    )
    token_row = result.scalar_one_or_none()
    if not token_row:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

    if not token_row.client.active:
        raise HTTPException(status_code=401, detail="Cliente revocado")

    return ExtClientContext(client=token_row.client, scopes=token_row.scopes)


def require_scope(scope: str) -> Any:
    async def dep(ctx: ExtClientContext = Depends(get_ext_client)) -> ExtClientContext:
        if not ctx.has_scope(scope):
            raise ForbiddenException(detail=f"Scope '{scope}' requerido")
        return ctx

    return Depends(dep)


def require_ocr(scope: str) -> Any:
    """Like `require_scope` for the OCR endpoints, plus the client's own rate
    limit (falls back to THROTTLE_OCR) and, for writes, the monthly page quota."""
    from app.config import settings
    from app.ratelimit import enforce as rl_enforce
    from app.repositories import client_usage as usage_repo

    async def dep(
        response: Response,
        ctx: ExtClientContext = Depends(get_ext_client),
        db: AsyncSession = Depends(get_db),
    ) -> ExtClientContext:
        if not ctx.has_scope(scope):
            raise ForbiddenException(detail=f"Scope '{scope}' requerido")

        raw = ctx.client.rate_limit or settings.throttle_ocr
        limit, per = settings.throttle(raw)
        await rl_enforce(f"ext_ocr:{ctx.client.id}", limit, per, response=response)

        if scope == "ocr:write":
            quota = ctx.client.monthly_page_quota or settings.ocr_default_monthly_page_quota
            if quota:
                used = await usage_repo.month_pages(db, ctx.client.id)
                response.headers["X-Quota-Limit"] = str(quota)
                response.headers["X-Quota-Remaining"] = str(max(0, quota - used))
                if used >= quota:
                    raise HTTPException(
                        status_code=429,
                        detail=f"Cuota mensual agotada ({used}/{quota} páginas).",
                        headers={"X-Quota-Limit": str(quota), "X-Quota-Remaining": "0"},
                    )
        return ctx

    return Depends(dep)
