from pydantic import BaseModel

from app.schemas.document import DocumentStats
from app.schemas.ocr import OcrStats


class RecentDocument(BaseModel):
    id: str
    original_filename: str | None = None
    mode: str
    status: str
    doc_type: str | None = None
    lang: str
    page_count: int | None = None
    processing_ms: int | None = None
    created_at: str


class DashboardResponse(BaseModel):
    documents: DocumentStats
    jobs: OcrStats
    recent: list[RecentDocument]
