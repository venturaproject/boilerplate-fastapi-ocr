from __future__ import annotations

import uuid
from dataclasses import dataclass, field, fields
from datetime import UTC, datetime


@dataclass(frozen=True)
class DomainEvent:
    """Hecho de negocio ya ocurrido.

    Las subclases añaden sus campos. ``name()`` es el identificador estable que
    usan el outbox y los subscribers (p.ej. ``"document.classified"``).
    """

    aggregate_id: str
    aggregate_type: str
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    occurred_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))

    @classmethod
    def name(cls) -> str:
        raise NotImplementedError

    def payload(self) -> dict:
        skip = {"aggregate_id", "aggregate_type", "event_id", "occurred_at"}
        data: dict = {}
        for f in fields(self):
            if f.name in skip:
                continue
            value = getattr(self, f.name)
            data[f.name] = value.isoformat() if isinstance(value, datetime) else value
        return data
