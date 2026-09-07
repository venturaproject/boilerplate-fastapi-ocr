from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

DocumentMode = Literal["sync", "async", "classify"]
DocumentStatus = Literal["pending", "done", "error"]


class DocumentOut(BaseModel):
    id: uuid.UUID
    api_client_id: uuid.UUID | None = None
    created_by_user_id: uuid.UUID | None = None
    ocr_job_id: uuid.UUID | None = None
    mode: DocumentMode
    status: DocumentStatus
    original_filename: str | None = None
    content_type: str | None = None
    size_bytes: int
    lang: str
    page_count: int | None = None
    processing_ms: int | None = None
    doc_type: str | None = None
    doc_type_confidence: float | None = None
    char_count: int | None = None
    text_excerpt: str | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    data: list[DocumentOut]
    current_page: int
    last_page: int
    per_page: int
    total: int


class DocumentStats(BaseModel):
    total: int = 0
    last_24h: int = 0
    by_mode: dict[str, int] = {}
    by_status: dict[str, int] = {}
    by_doc_type: dict[str, int] = {}
    processing_ms_avg: float | None = None
    processing_ms_p95: float | None = None
