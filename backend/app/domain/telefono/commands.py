from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from app.cqrs import Command


@dataclass(frozen=True)
class CreateTelefono(Command):
    data: dict[str, Any]


@dataclass(frozen=True)
class UpdateTelefono(Command):
    id: uuid.UUID
    data: dict[str, Any]


@dataclass(frozen=True)
class DeleteTelefono(Command):
    id: uuid.UUID
