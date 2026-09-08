from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.cqrs.messages import Command, Query
from app.cqrs.registry import get_command_handler, get_query_handler
from app.events.collector import collector_scope, drain_events

logger = logging.getLogger("app.cqrs")


class CommandBus:
    async def dispatch(self, session: AsyncSession, command: Command) -> Any:
        handler = get_command_handler(type(command))
        name = type(command).__name__
        logger.info("command.dispatch %s", name)
        with collector_scope():
            try:
                result = await handler(session, command)
            except Exception:
                logger.exception("command.failed %s", name)
                raise
            await self._flush_events(session)
        logger.info("command.ok %s", name)
        return result

    @staticmethod
    async def _flush_events(session: AsyncSession) -> None:
        events = drain_events()
        if not events:
            return
        from app.events.models import OutboxMessage

        for e in events:
            session.add(
                OutboxMessage(
                    event_name=type(e).name(),
                    aggregate_type=e.aggregate_type,
                    aggregate_id=str(e.aggregate_id),
                    payload=e.payload(),
                )
            )
        await session.flush()


class QueryBus:
    async def ask(self, session: AsyncSession, query: Query) -> Any:
        handler = get_query_handler(type(query))
        return await handler(session, query)


command_bus = CommandBus()
query_bus = QueryBus()
