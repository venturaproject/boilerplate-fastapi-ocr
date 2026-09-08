import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AuditEvent(Base):
    """Append-only log of security-relevant actions (logins, RBAC changes, API
    client lifecycle). Written best-effort in its own transaction."""

    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    action: Mapped[str] = mapped_column(String(64), index=True)  # e.g. "auth.login.failed"
    actor_type: Mapped[str] = mapped_column(String(16))  # user | client | anonymous | system
    actor_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    actor_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    target: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<AuditEvent {self.action} {self.actor_label}>"
