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
    text: str = Field(description="Page lines joined by newline, in reading order")


class OcrResult(BaseModel):
    engine: str
    lang: str
    page_count: int
    pages: list[OcrPage]
    text: str = Field(description="Full document text")
    processing_ms: int
    cached: bool = False


class OcrJobSummary(BaseModel):
    """Job metadata without the (potentially large) OCR result — used in listings."""

    id: uuid.UUID
    status: OcrJobStatus
    original_filename: str | None = None
    content_type: str | None = None
    size_bytes: int
    lang: str
    page_count: int | None = None
    processing_ms: int | None = None
    callback_url: str | None = None
    callback_status: str | None = None
    error: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None

    model_config = {"from_attributes": True}


class OcrJobOut(OcrJobSummary):
    result: OcrResult | None = None


class OcrJobListResponse(BaseModel):
    data: list[OcrJobSummary]
    total: int
    page: int
    per_page: int


class OcrStats(BaseModel):
    pending: int = 0
    processing: int = 0
    done: int = 0
    error: int = 0
    oldest_pending_age_seconds: float | None = None
    processing_ms_avg: float | None = None
    processing_ms_p95: float | None = None
