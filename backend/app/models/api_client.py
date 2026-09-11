import hashlib
import hmac
import secrets
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ApiClient(Base):
    __tablename__ = "api_clients"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    client_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    secret_hash: Mapped[str] = mapped_column(String(64))
    scopes: Mapped[list[str]] = mapped_column(JSON, default=list)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    rate_limit: Mapped[str | None] = mapped_column(String(20), nullable=True)  # "<n>/<secs>", overrides THROTTLE_OCR
    monthly_page_quota: Mapped[int | None] = mapped_column(Integer, nullable=True)  # None/0 = unlimited
    # "none"|"rules"|"llm", overrides OCR_EXTRACTOR for this client's requests; None = inherit
    # the global setting. Lets a tenant that can't have its documents leave to a third-party
    # LLM be pinned to "rules"/"none" even while OCR_EXTRACTOR=llm elsewhere.
    ocr_extractor_override: Mapped[str | None] = mapped_column(String(10), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tokens: Mapped[list["ApiClientToken"]] = relationship(
        "ApiClientToken", back_populates="client", cascade="all, delete-orphan", lazy="selectin"
    )

    @staticmethod
    def generate_credentials() -> tuple[str, str, str]:
        client_id = "cli_" + secrets.token_hex(16)
        secret = secrets.token_urlsafe(40)
        secret_hash = hashlib.sha256(secret.encode()).hexdigest()
        return client_id, secret, secret_hash

    def verify_secret(self, secret: str) -> bool:
        return hmac.compare_digest(hashlib.sha256(secret.encode()).hexdigest(), self.secret_hash)

    def __repr__(self) -> str:
        return f"<ApiClient {self.name}>"


class ApiClientToken(Base):
    __tablename__ = "api_client_tokens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("api_clients.id", ondelete="CASCADE"))
    scopes: Mapped[list[str]] = mapped_column(JSON, default=list)
    access_token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    refresh_token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    access_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    refresh_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    client: Mapped["ApiClient"] = relationship("ApiClient", back_populates="tokens", lazy="selectin")

    def __repr__(self) -> str:
        return f"<ApiClientToken client_id={self.client_id}>"


class ClientUsage(Base):
    """Per-client OCR usage, one row per calendar month (`YYYY-MM`)."""

    __tablename__ = "client_usage"
    __table_args__ = (UniqueConstraint("api_client_id", "period", name="uq_client_usage_period"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    api_client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("api_clients.id", ondelete="CASCADE"), index=True)
    period: Mapped[str] = mapped_column(String(7))  # YYYY-MM
    pages: Mapped[int] = mapped_column(Integer, default=0)
    requests: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
