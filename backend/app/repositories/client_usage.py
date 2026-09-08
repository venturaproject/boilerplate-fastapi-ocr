import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_client import ClientUsage


def current_period() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m")


async def increment(db: AsyncSession, api_client_id: uuid.UUID, *, pages: int = 0, requests: int = 1) -> None:
    period = current_period()
    stmt = (
        pg_insert(ClientUsage)
        .values(api_client_id=api_client_id, period=period, pages=pages, requests=requests)
        .on_conflict_do_update(
            constraint="uq_client_usage_period",
            set_={
                "pages": ClientUsage.pages + pages,
                "requests": ClientUsage.requests + requests,
                "updated_at": datetime.now(tz=UTC),
            },
        )
    )
    await db.execute(stmt)
    await db.flush()


async def get_month(db: AsyncSession, api_client_id: uuid.UUID) -> ClientUsage | None:
    result = await db.execute(
        select(ClientUsage).where(
            ClientUsage.api_client_id == api_client_id,
            ClientUsage.period == current_period(),
        )
    )
    return result.scalar_one_or_none()


async def month_pages(db: AsyncSession, api_client_id: uuid.UUID) -> int:
    row = await get_month(db, api_client_id)
    return row.pages if row else 0
