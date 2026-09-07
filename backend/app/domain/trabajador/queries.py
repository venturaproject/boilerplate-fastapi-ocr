from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.cqrs import Query


@dataclass(frozen=True)
class ListTrabajadores(Query):
    page: int = 1
    per_page: int = 20
    search: str | None = None
    estado: str | None = None
    departamento: str | None = None


@dataclass(frozen=True)
class GetTrabajador(Query):
    id: uuid.UUID
