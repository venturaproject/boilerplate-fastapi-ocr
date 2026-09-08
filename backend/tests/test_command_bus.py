from __future__ import annotations

from dataclasses import dataclass

import pytest
from sqlalchemy import select

from app.cqrs import Command, HandlerNotFound, command_bus, command_handler
from app.events.collector import record_events
from app.events.models import OutboxMessage
from tests._helpers import DummyEvent, registry_guard


@dataclass(frozen=True)
class _Ping(Command):
    value: int


@dataclass(frozen=True)
class _Boom(Command):
    pass


async def test_routes_to_handler(session):
    with registry_guard():

        async def handler(s, cmd):
            return cmd.value * 2

        command_handler(_Ping)(handler)
        assert await command_bus.dispatch(session, _Ping(value=21)) == 42


async def test_unknown_command_raises(session):
    with pytest.raises(HandlerNotFound):
        await command_bus.dispatch(session, _Ping(value=1))


async def test_handler_error_rolls_back_outbox(session):
    from app.database import AsyncSessionLocal

    with registry_guard():

        async def handler(s, cmd):
            record_events([DummyEvent(aggregate_id="1", aggregate_type="X")])
            raise RuntimeError("explota")

        command_handler(_Boom)(handler)
        with pytest.raises(RuntimeError):
            async with AsyncSessionLocal() as s, s.begin():
                await command_bus.dispatch(s, _Boom())

    async with AsyncSessionLocal() as s:
        rows = (await s.execute(select(OutboxMessage))).scalars().all()
    assert rows == []
