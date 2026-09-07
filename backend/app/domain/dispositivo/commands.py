from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from app.cqrs import Command


@dataclass(frozen=True)
class CreateDispositivo(Command):
    data: dict[str, Any]


@dataclass(frozen=True)
class UpdateDispositivo(Command):
    id: uuid.UUID
    data: dict[str, Any]


@dataclass(frozen=True)
class DeleteDispositivo(Command):
    id: uuid.UUID
