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


class DocClassification(BaseModel):
    doc_type: str | None = Field(description="Detected document type, or null if unknown")
    confidence: float = Field(ge=0.0, le=1.0, description="Dominance of the top type")
    scores: dict[str, float] = Field(default_factory=dict, description="Normalised score per type")


class DocExtractionField(BaseModel):
    value: str
    raw: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class DocExtraction(BaseModel):
    doc_type: str | None = None
    fields: dict[str, DocExtractionField] = Field(default_factory=dict)


class OcrResult(BaseModel):
    engine: str
    lang: str
    lang_detected: bool = Field(default=False, description="True if `lang` was auto-detected")
    page_count: int
    pages: list[OcrPage]
    text: str = Field(description="Full document text")
    processing_ms: int
    cached: bool = False
    classification: DocClassification | None = None
    extraction: DocExtraction | None = None


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
    doc_type: str | None = None
    callback_url: str | None = None
    callback_status: str | None = None
    callback_attempts: int = 0
    callback_last_error: str | None = None
    next_callback_at: datetime | None = None
    batch_id: uuid.UUID | None = None
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


class OcrBatchResponse(BaseModel):
    batch_id: uuid.UUID
    count: int
    jobs: list[OcrJobSummary]


class OcrBatchStatus(BaseModel):
    batch_id: uuid.UUID
    counts: dict[str, int]
    total: int
    jobs: list[OcrJobSummary]


class OcrUsageOut(BaseModel):
    period: str
    pages: int
    requests: int
    monthly_page_quota: int | None = None
    quota_remaining: int | None = None
    rate_limit: str | None = None


class ClassifyOut(BaseModel):
    doc_type: str | None
    confidence: float
    scores: dict[str, float]
    lang: str
    page_count: int
    text_excerpt: str
    extraction: DocExtraction | None = None


class OcrStats(BaseModel):
    pending: int = 0
    processing: int = 0
    done: int = 0
    error: int = 0
    oldest_pending_age_seconds: float | None = None
    processing_ms_avg: float | None = None
    processing_ms_p95: float | None = None
    by_doc_type: dict[str, int] = {}
