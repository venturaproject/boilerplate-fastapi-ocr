import hashlib
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.api_client import ApiClient, ApiClientToken


async def list_api_clients(db: AsyncSession) -> list[ApiClient]:
    result = await db.execute(select(ApiClient).order_by(ApiClient.created_at.desc()))
    return list(result.scalars().all())


async def get_api_client_by_id(db: AsyncSession, client_id: uuid.UUID) -> ApiClient | None:
    result = await db.execute(select(ApiClient).where(ApiClient.id == client_id))
    return result.scalar_one_or_none()


async def get_api_client_by_client_id(db: AsyncSession, client_id: str) -> ApiClient | None:
    result = await db.execute(select(ApiClient).where(ApiClient.client_id == client_id, ApiClient.active == True))  # noqa: E712
    return result.scalar_one_or_none()


async def create_api_client(db: AsyncSession, name: str, scopes: list[str]) -> tuple[ApiClient, str]:
    client_id, secret, secret_hash = ApiClient.generate_credentials()
    client = ApiClient(
        name=name,
        client_id=client_id,
        secret_hash=secret_hash,
        scopes=scopes,
    )
    db.add(client)
    await db.flush()
    await db.refresh(client)
    return client, secret


async def revoke_api_client(db: AsyncSession, client: ApiClient) -> None:
    client.active = False
    await db.execute(delete(ApiClientToken).where(ApiClientToken.client_id == client.id))
    await db.flush()


_UNSET: Any = object()


async def update_api_client(
    db: AsyncSession,
    client: ApiClient,
    *,
    rate_limit: str | None = _UNSET,
    monthly_page_quota: int | None = _UNSET,
) -> ApiClient:
    if rate_limit is not _UNSET:
        client.rate_limit = rate_limit or None
    if monthly_page_quota is not _UNSET:
        client.monthly_page_quota = monthly_page_quota or None
    await db.flush()
    return client


async def rotate_secret(db: AsyncSession, client: ApiClient) -> str:
    _, secret, secret_hash = ApiClient.generate_credentials()
    client.secret_hash = secret_hash
    await db.execute(delete(ApiClientToken).where(ApiClientToken.client_id == client.id))
    await db.flush()
    return secret


async def create_token(
    db: AsyncSession,
    client: ApiClient,
    access_token: str,
    refresh_token: str,
    access_expires_at: datetime,
    refresh_expires_at: datetime,
) -> ApiClientToken:
    token = ApiClientToken(
        client_id=client.id,
        scopes=client.scopes,
        access_token_hash=hashlib.sha256(access_token.encode()).hexdigest(),
        refresh_token_hash=hashlib.sha256(refresh_token.encode()).hexdigest(),
        access_expires_at=access_expires_at,
        refresh_expires_at=refresh_expires_at,
    )
    db.add(token)
    await db.flush()
    return token


async def get_token_by_refresh_hash(
    db: AsyncSession, refresh_hash: str, *, for_update: bool = False
) -> ApiClientToken | None:
    stmt = (
        select(ApiClientToken)
        .options(selectinload(ApiClientToken.client))
        .where(
            ApiClientToken.refresh_token_hash == refresh_hash,
            ApiClientToken.refresh_expires_at > datetime.now(tz=UTC),
        )
    )
    if for_update:
        stmt = stmt.with_for_update(of=ApiClientToken)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def delete_token(db: AsyncSession, token: ApiClientToken) -> None:
    await db.delete(token)
    await db.flush()
