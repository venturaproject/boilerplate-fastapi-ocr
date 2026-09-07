from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.cqrs import Query


@dataclass(frozen=True)
class ListTelefonos(Query):
    page: int = 1
    per_page: int = 20
    search: str | None = None
    activo: bool | None = None
    estado_id: uuid.UUID | None = None
    trabajador_id: uuid.UUID | None = None


@dataclass(frozen=True)
class GetTelefono(Query):
    id: uuid.UUID
