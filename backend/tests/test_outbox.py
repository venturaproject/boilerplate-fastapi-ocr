from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select

from app.cqrs import Command, command_bus, command_handler
from app.database import AsyncSessionLocal
from app.events.collector import record_events
from app.events.models import OutboxMessage
from tests._helpers import DummyEvent, registry_guard


@dataclass(frozen=True)
class _DoThing(Command):
    pass


async def test_events_recorded_in_handler_land_in_outbox():
    with registry_guard():
        @command_handler(_DoThing)
        async def handler(s, cmd):
            record_events([DummyEvent(aggregate_id="7", aggregate_type="Thing", note="hola")])

        async with AsyncSessionLocal() as s, s.begin():
            await command_bus.dispatch(s, _DoThing())

    async with AsyncSessionLocal() as s:
        rows = (await s.execute(select(OutboxMessage))).scalars().all()

    assert len(rows) == 1
    assert rows[0].event_name == "test.dummy"
    assert rows[0].aggregate_id == "7"
    assert rows[0].payload == {"note": "hola"}


async def test_record_events_outside_unit_is_noop():
    record_events([DummyEvent(aggregate_id="1", aggregate_type="Thing")])
    async with AsyncSessionLocal() as s:
        rows = (await s.execute(select(OutboxMessage))).scalars().all()
    assert rows == []
