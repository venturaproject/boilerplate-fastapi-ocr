import hashlib
import secrets
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, func
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
        return hashlib.sha256(secret.encode()).hexdigest() == self.secret_hash

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
