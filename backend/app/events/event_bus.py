from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

logger = logging.getLogger("app.events")

Subscriber = Callable[[dict], Awaitable[None]]


class EventBus:
    """Pub/sub local en proceso. Los subscribers se ejecutan cuando el worker
    publica un mensaje del outbox."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Subscriber]] = {}

    def subscribe(self, event_name: str, fn: Subscriber) -> None:
        self._subscribers.setdefault(event_name, []).append(fn)

    async def publish(self, event_name: str, payload: dict) -> int:
        subs = self._subscribers.get(event_name, [])
        for fn in subs:
            logger.debug("event.deliver %s -> %s", event_name, fn.__qualname__)
            await fn(payload)
        return len(subs)

    def clear(self) -> None:
        """Sólo para tests."""
        self._subscribers.clear()


event_bus = EventBus()


def subscribe(event_name: str) -> Callable[[Subscriber], Subscriber]:
    def decorator(fn: Subscriber) -> Subscriber:
        event_bus.subscribe(event_name, fn)
        return fn

    return decorator
