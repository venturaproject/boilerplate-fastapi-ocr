from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

OcrJobStatus = Literal["pending", "processing", "done", "error"]


class OcrLine(BaseModel):
    """A single text line detected on a page."""

    text: str
    confidence: float = Field(ge=0.0, le=1.0)
    box: list[list[float]] = Field(description="Polygon, 4 points [[x, y], ...]")


class OcrPage(BaseModel):
    page: int
    width: int
    height: int
    lines: list[OcrLine]
    text: str = Field(description="Page lines joined by newline")


class OcrResult(BaseModel):
    engine: str
    lang: str
    page_count: int
    pages: list[OcrPage]
    text: str = Field(description="Full document text")
    processing_ms: int


class OcrJobOut(BaseModel):
    id: uuid.UUID
    status: OcrJobStatus
    original_filename: str | None = None
    content_type: str | None = None
    size_bytes: int
    lang: str
    page_count: int | None = None
    callback_url: str | None = None
    callback_status: str | None = None
    error: str | None = None
    result: OcrResult | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None

    model_config = {"from_attributes": True}


class OcrJobListResponse(BaseModel):
    data: list[OcrJobOut]
    total: int
    page: int
    per_page: int
