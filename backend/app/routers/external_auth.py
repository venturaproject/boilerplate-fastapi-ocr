from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.ratelimit import rate_limit
from app.repositories import api_client as client_repo
from app.schemas.api_client import ExtRefreshRequest, ExtTokenRequest, ExtTokenResponse
from app.services.api_client import (
    access_expires_at,
    access_ttl_seconds,
    generate_opaque_token,
    hash_token,
    refresh_expires_at,
)

router = APIRouter(prefix="/api/ext/auth", tags=["external-auth"])

_ea_limit, _ea_per = settings.throttle(settings.throttle_ext_auth)
_ext_auth_rl = Depends(rate_limit("ext_auth", _ea_limit, _ea_per))


@router.post("/token", dependencies=[_ext_auth_rl])
async def ext_token(body: ExtTokenRequest, db: AsyncSession = Depends(get_db)) -> ExtTokenResponse:
    client = await client_repo.get_api_client_by_client_id(db, body.client_id)
    if not client:
        raise HTTPException(status_code=401, detail="Credenciales inválidas.")

    if not client.verify_secret(body.client_secret):
        raise HTTPException(status_code=401, detail="Credenciales inválidas.")

    access_token = generate_opaque_token()
    refresh_token = generate_opaque_token()

    await client_repo.create_token(
        db,
        client=client,
        access_token=access_token,
        refresh_token=refresh_token,
        access_expires_at=access_expires_at(),
        refresh_expires_at=refresh_expires_at(),
    )

    return ExtTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=access_ttl_seconds(),
        scopes=client.scopes,
    )


@router.post("/refresh", dependencies=[_ext_auth_rl])
async def ext_refresh(body: ExtRefreshRequest, db: AsyncSession = Depends(get_db)) -> ExtTokenResponse:
    refresh_hash = hash_token(body.refresh_token)
    # FOR UPDATE: dos refresh concurrentes con el mismo token se serializan; el
    # segundo encuentra la fila ya borrada -> 401.
    old_token = await client_repo.get_token_by_refresh_hash(db, refresh_hash, for_update=True)
    if not old_token:
        raise HTTPException(status_code=401, detail="Refresh token inválido o expirado.")

    if not old_token.client.active:
        raise HTTPException(status_code=401, detail="Cliente revocado.")

    client = old_token.client
    await client_repo.delete_token(db, old_token)

    access_token = generate_opaque_token()
    refresh_token = generate_opaque_token()

    await client_repo.create_token(
        db,
        client=client,
        access_token=access_token,
        refresh_token=refresh_token,
        access_expires_at=access_expires_at(),
        refresh_expires_at=refresh_expires_at(),
    )

    return ExtTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=access_ttl_seconds(),
        scopes=client.scopes,
    )
