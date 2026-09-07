from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select

from app.cqrs import Command, command_handler
from app.database import AsyncSessionLocal
from app.events.inbox import process_inbox_batch, store
from app.events.models import InboxMessage
from app.events.translators import inbox_translator
from tests._helpers import registry_guard


@dataclass(frozen=True)
class _Ingest(Command):
    name: str


async def test_duplicate_message_id_not_stored_twice(session):
    _, created1 = await store(session, source="t", message_id="m1", event_name="e", payload={"n": "a"})
    await session.commit()
    _, created2 = await store(session, source="t", message_id="m1", event_name="e", payload={"n": "b"})
    await session.commit()

    assert created1 is True
    assert created2 is False
    async with AsyncSessionLocal() as s:
        count = (
            await s.execute(
                select(func.count()).select_from(InboxMessage).where(InboxMessage.message_id == "m1")
            )
        ).scalar_one()
    assert count == 1


async def test_processor_translates_and_dispatches(session):
    dispatched: list[str] = []
    with registry_guard():
        async def handler(s, cmd):
            dispatched.append(cmd.name)

        command_handler(_Ingest)(handler)
        inbox_translator("t", "thing.created")(lambda p: _Ingest(name=p["name"]))

        await store(session, source="t", message_id="m2", event_name="thing.created", payload={"name": "x"})
        await session.commit()
        assert await process_inbox_batch() == 1

    assert dispatched == ["x"]
    async with AsyncSessionLocal() as s:
        row = (await s.execute(select(InboxMessage).where(InboxMessage.message_id == "m2"))).scalar_one()
    assert row.status == "processed"


async def test_unknown_event_retries(session):
    await store(session, source="t", message_id="m3", event_name="nope", payload={})
    await session.commit()
    await process_inbox_batch()

    async with AsyncSessionLocal() as s:
        row = (await s.execute(select(InboxMessage).where(InboxMessage.message_id == "m3"))).scalar_one()
    assert row.status == "pending"
    assert row.attempts == 1
