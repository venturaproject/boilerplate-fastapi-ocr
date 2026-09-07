from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from app.cqrs import Command


@dataclass(frozen=True)
class CreateTrabajador(Command):
    data: dict[str, Any]


@dataclass(frozen=True)
class UpdateTrabajador(Command):
    id: uuid.UUID
    data: dict[str, Any]


@dataclass(frozen=True)
class DeleteTrabajador(Command):
    id: uuid.UUID


@dataclass(frozen=True)
class SyncTrabajadorFromERP(Command):
    """Alta/actualización de un trabajador desde un evento del ERP Synergy."""

    synergy_res_id: int | None = None
    nombre_completo: str = ""
    email: str | None = None
    estado: str = "activo"
    emp_stat: str | None = None
    loc: str | None = None
    ubicacion: str | None = None
    ciudad: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)
