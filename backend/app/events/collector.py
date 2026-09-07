from __future__ import annotations

import contextlib
from collections.abc import Iterable, Iterator
from contextvars import ContextVar

from app.events.base_event import DomainEvent

# Eventos de dominio de la unidad de trabajo actual. El ``command_bus`` abre un
# ``collector_scope()`` alrededor de cada handler y, al terminar, vuelca lo
# acumulado a ``outbox_messages``. Fuera de un scope, ``record_events`` es no-op.
_events: ContextVar[list[DomainEvent] | None] = ContextVar("domain_events", default=None)


def record_events(events: Iterable[DomainEvent]) -> None:
    """Lo llaman los handlers tras persistir el cambio de negocio."""
    bucket = _events.get()
    if bucket is None:
        return
    bucket.extend(events)


def drain_events() -> list[DomainEvent]:
    """Devuelve y limpia los eventos acumulados (lo llama el command_bus)."""
    bucket = _events.get()
    if not bucket:
        return []
    bucket_copy = list(bucket)
    bucket.clear()
    return bucket_copy


@contextlib.contextmanager
def collector_scope() -> Iterator[None]:
    token = _events.set([])
    try:
        yield
    finally:
        _events.reset(token)
