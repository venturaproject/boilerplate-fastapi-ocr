from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.cqrs import Command


@dataclass(frozen=True)
class DeleteDocument(Command):
    id: uuid.UUID
