"""Kernel de eventos: outbox transaccional, inbox idempotente, event bus local.

Los eventos de dominio que un handler registra con ``record_events()`` los vuelca
al ``outbox_messages`` el propio ``command_bus`` (misma transacción que el cambio
de negocio). El ``worker`` (``python -m app.events.worker``) drena outbox e inbox.
"""

from app.events.base_event import DomainEvent
from app.events.collector import collector_scope, record_events
from app.events.event_bus import event_bus, subscribe
from app.events.translators import inbox_translator

__all__ = [
    "DomainEvent",
    "collector_scope",
    "event_bus",
    "inbox_translator",
    "record_events",
    "subscribe",
]
