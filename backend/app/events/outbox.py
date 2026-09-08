from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update

from app.database import AsyncSessionLocal
from app.events.event_bus import event_bus
from app.events.models import OutboxMessage
from app.events.retry import next_backoff

logger = logging.getLogger("app.events")


async def process_outbox_batch(*, batch_size: int = 50) -> int:
    """Reclama un lote (SKIP LOCKED) y publica cada mensaje en su propia
    transacción. Devuelve cuántos se procesaron."""
    ids = await _claim(batch_size)
    for msg_id in ids:
        await _deliver_one(msg_id)
    return len(ids)


async def _claim(batch_size: int) -> list[uuid.UUID]:
    now = datetime.now(tz=UTC)
    async with AsyncSessionLocal() as session, session.begin():
        rows = (
            (
                await session.execute(
                    select(OutboxMessage.id)
                    .where(OutboxMessage.status == "pending", OutboxMessage.available_at <= now)
                    .order_by(OutboxMessage.available_at)
                    .limit(batch_size)
                    .with_for_update(skip_locked=True)
                )
            )
            .scalars()
            .all()
        )
        if rows:
            await session.execute(update(OutboxMessage).where(OutboxMessage.id.in_(rows)).values(status="processing"))
        return list(rows)


async def _deliver_one(msg_id: uuid.UUID) -> None:
    async with AsyncSessionLocal() as session, session.begin():
        msg = await session.get(OutboxMessage, msg_id)
        if msg is None:
            return
        try:
            delivered = await event_bus.publish(msg.event_name, msg.payload)
        except Exception as exc:
            _mark_retry(msg, exc)
            logger.warning("outbox.retry %s (%s)", msg.event_name, exc)
            return
        msg.status = "done"
        msg.processed_at = datetime.now(tz=UTC)
        msg.last_error = ""
        logger.info("outbox.done %s subscribers=%s", msg.event_name, delivered)


def _mark_retry(msg: OutboxMessage, exc: Exception) -> None:
    msg.attempts += 1
    msg.last_error = str(exc)
    if msg.attempts >= msg.max_attempts:
        msg.status = "failed"
        msg.processed_at = datetime.now(tz=UTC)
        logger.error("outbox.failed %s tras %s intentos", msg.event_name, msg.attempts)
    else:
        msg.status = "pending"
        msg.available_at = datetime.now(tz=UTC) + next_backoff(msg.attempts)
