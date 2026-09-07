from __future__ import annotations

from dataclasses import dataclass

from app.cqrs.registry import _command_handlers, _query_handlers
from app.events.base_event import DomainEvent
from app.events.event_bus import event_bus
from app.events.translators import _translators


@dataclass(frozen=True)
class DummyEvent(DomainEvent):
    note: str = ""

    @classmethod
    def name(cls) -> str:
        return "test.dummy"


class registry_guard:
    """Restaura el estado de buses / event bus / traductores tras el test."""

    def __enter__(self):
        self._cmd = dict(_command_handlers)
        self._qry = dict(_query_handlers)
        self._subs = {k: list(v) for k, v in event_bus._subscribers.items()}
        self._tr = dict(_translators)
        return self

    def __exit__(self, *exc):
        _command_handlers.clear()
        _command_handlers.update(self._cmd)
        _query_handlers.clear()
        _query_handlers.update(self._qry)
        event_bus._subscribers.clear()
        event_bus._subscribers.update(self._subs)
        _translators.clear()
        _translators.update(self._tr)
