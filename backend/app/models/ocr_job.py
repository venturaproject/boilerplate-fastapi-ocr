import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class OcrJob(Base):
    __tablename__ = "ocr_jobs"
    __table_args__ = (
        Index("ix_ocr_jobs_status_created", "status", "created_at"),
        Index("ix_ocr_jobs_status_started", "status", "started_at"),
        Index("ix_ocr_jobs_client_created", "api_client_id", "created_at"),
        Index("ix_ocr_jobs_next_callback", "next_callback_at"),
        Index("ix_ocr_jobs_batch", "batch_id"),
    )

    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_DONE = "done"
    STATUS_ERROR = "error"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    api_client_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("api_clients.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    batch_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)

    status: Mapped[str] = mapped_column(String(20), default=STATUS_PENDING)
    original_filename: Mapped[str | None] = mapped_column(String(512), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    storage_path: Mapped[str] = mapped_column(String(1024))
    lang: Mapped[str] = mapped_column(String(16), default="es")
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    processing_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    doc_type: Mapped[str | None] = mapped_column(String(40), nullable=True)

    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    callback_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    callback_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    callback_attempts: Mapped[int] = mapped_column(Integer, default=0)
    callback_last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    next_callback_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<OcrJob {self.id} {self.status}>"
