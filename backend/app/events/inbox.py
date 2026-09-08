from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.cqrs.bus import command_bus
from app.database import AsyncSessionLocal
from app.events.models import InboxMessage
from app.events.retry import next_backoff
from app.events.translators import translate

logger = logging.getLogger("app.events")


async def store(
    session: AsyncSession,
    *,
    source: str,
    message_id: str,
    event_name: str,
    payload: dict,
) -> tuple[InboxMessage, bool]:
    """Guarda el mensaje si es nuevo. Devuelve ``(row, created)``.
    ``created=False`` = reenvío duplicado ya conocido."""
    stmt = (
        pg_insert(InboxMessage)
        .values(source=source, message_id=message_id, event_name=event_name, payload=payload)
        .on_conflict_do_nothing(index_elements=["source", "message_id"])
        .returning(InboxMessage.id)
    )
    inserted_id = (await session.execute(stmt)).scalar_one_or_none()
    row = (
        await session.execute(
            select(InboxMessage).where(InboxMessage.source == source, InboxMessage.message_id == message_id)
        )
    ).scalar_one()
    return row, inserted_id is not None


async def process_inbox_batch(*, batch_size: int = 50) -> int:
    ids = await _claim(batch_size)
    for msg_id in ids:
        await _handle_one(msg_id)
    return len(ids)


async def _claim(batch_size: int) -> list[uuid.UUID]:
    now = datetime.now(tz=UTC)
    async with AsyncSessionLocal() as session, session.begin():
        rows = (
            (
                await session.execute(
                    select(InboxMessage.id)
                    .where(InboxMessage.status == "pending", InboxMessage.available_at <= now)
                    .order_by(InboxMessage.available_at)
                    .limit(batch_size)
                    .with_for_update(skip_locked=True)
                )
            )
            .scalars()
            .all()
        )
        if rows:
            await session.execute(update(InboxMessage).where(InboxMessage.id.in_(rows)).values(status="processing"))
        return list(rows)


async def _handle_one(msg_id: uuid.UUID) -> None:
    try:
        async with AsyncSessionLocal() as session, session.begin():
            msg = await session.get(InboxMessage, msg_id)
            if msg is None:
                return
            command = translate(msg.source, msg.event_name, msg.payload)
            # el command_bus vuelca los eventos de dominio al outbox en esta
            # misma transacción
            await command_bus.dispatch(session, command)
            msg.status = "processed"
            msg.processed_at = datetime.now(tz=UTC)
            msg.last_error = ""
            src, mid = msg.source, msg.message_id
    except Exception as exc:
        await _mark_retry(msg_id, str(exc))
        logger.warning("inbox.retry %s (%s)", msg_id, exc)
        return
    logger.info("inbox.processed %s:%s", src, mid)


async def _mark_retry(msg_id: uuid.UUID, error: str) -> None:
    async with AsyncSessionLocal() as session, session.begin():
        msg = await session.get(InboxMessage, msg_id)
        if msg is None:
            return
        msg.attempts += 1
        msg.last_error = error
        if msg.attempts >= msg.max_attempts:
            msg.status = "failed"
            msg.processed_at = datetime.now(tz=UTC)
            logger.error("inbox.failed %s:%s tras %s intentos", msg.source, msg.message_id, msg.attempts)
        else:
            msg.status = "pending"
            msg.available_at = datetime.now(tz=UTC) + next_backoff(msg.attempts)
