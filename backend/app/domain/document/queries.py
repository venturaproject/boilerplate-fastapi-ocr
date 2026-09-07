from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.cqrs import Query


@dataclass(frozen=True)
class ListDocuments(Query):
    page: int = 1
    per_page: int = 20
    search: str | None = None
    mode: str | None = None
    doc_type: str | None = None
    status: str | None = None


@dataclass(frozen=True)
class GetDocument(Query):
    id: uuid.UUID


@dataclass(frozen=True)
class GetDocumentStats(Query):
    pass
