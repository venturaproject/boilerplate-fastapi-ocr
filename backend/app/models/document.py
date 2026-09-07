import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Document(Base):
    """Durable registry of every document processed through the OCR API.

    One row per external call — synchronous (`POST /api/ext/ocr`), classification
    (`POST /api/ext/ocr/classify`) and asynchronous jobs (`POST /api/ext/ocr/jobs`).
    Async rows link back to the (purgeable) `ocr_jobs` row via `ocr_job_id`.
    """

    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_client_created", "api_client_id", "created_at"),
        Index("ix_documents_mode_created", "mode", "created_at"),
        Index("ix_documents_doc_type", "doc_type"),
    )

    MODE_SYNC = "sync"
    MODE_ASYNC = "async"
    MODE_CLASSIFY = "classify"

    STATUS_PENDING = "pending"
    STATUS_DONE = "done"
    STATUS_ERROR = "error"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    api_client_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("api_clients.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    ocr_job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ocr_jobs.id", ondelete="SET NULL"), nullable=True, unique=True
    )

    mode: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default=STATUS_DONE)
    original_filename: Mapped[str | None] = mapped_column(String(512), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    lang: Mapped[str] = mapped_column(String(16), default="es")
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    processing_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    doc_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    doc_type_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    char_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    text_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<Document {self.id} {self.mode}/{self.status}>"
