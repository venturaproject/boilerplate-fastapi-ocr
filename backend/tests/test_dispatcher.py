from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.events.event_bus import event_bus
from app.events.models import OutboxMessage
from app.events.outbox import process_outbox_batch
from tests._helpers import registry_guard


async def _add(**kw) -> None:
    defaults = {"event_name": "test.evt", "aggregate_type": "X", "aggregate_id": "1", "payload": {}}
    defaults.update(kw)
    async with AsyncSessionLocal() as s, s.begin():
        s.add(OutboxMessage(**defaults))


async def _get_one() -> OutboxMessage:
    async with AsyncSessionLocal() as s:
        return (await s.execute(select(OutboxMessage))).scalars().one()


async def test_success_marks_done():
    with registry_guard():
        seen: list[dict] = []

        async def sub(payload):
            seen.append(payload)

        event_bus.subscribe("test.evt", sub)
        await _add(payload={"k": 1})

        assert await process_outbox_batch() == 1

    assert seen == [{"k": 1}]
    msg = await _get_one()
    assert msg.status == "done"
    assert msg.processed_at is not None


async def test_failure_retries_with_backoff():
    with registry_guard():

        async def boom(payload):
            raise RuntimeError("nope")

        event_bus.subscribe("test.evt", boom)
        await _add(max_attempts=3)
        await process_outbox_batch()

    msg = await _get_one()
    assert msg.status == "pending"
    assert msg.attempts == 1
    assert msg.available_at > datetime.now(tz=UTC)
    assert "nope" in msg.last_error


async def test_exhausted_attempts_mark_failed():
    with registry_guard():

        async def boom(payload):
            raise RuntimeError("x")

        event_bus.subscribe("test.evt", boom)
        await _add(attempts=2, max_attempts=3)
        await process_outbox_batch()

    msg = await _get_one()
    assert msg.status == "failed"
    assert msg.attempts == 3


async def test_future_available_at_not_claimed():
    await _add(available_at=datetime.now(tz=UTC) + timedelta(hours=1))
    assert await process_outbox_batch() == 0
