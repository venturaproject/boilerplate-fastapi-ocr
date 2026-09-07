from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.cqrs import Query


@dataclass(frozen=True)
class ListDispositivos(Query):
    page: int = 1
    per_page: int = 20
    search: str | None = None
    estado: str | None = None
    trabajador_id: uuid.UUID | None = None


@dataclass(frozen=True)
class GetDispositivo(Query):
    id: uuid.UUID
