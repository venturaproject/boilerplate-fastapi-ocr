import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    guard_name: Mapped[str] = mapped_column(String(255), default="api")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # back-refs populated by Role.permissions relationship
    roles: Mapped[list["Role"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Role", secondary="role_permissions", back_populates="permissions", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Permission {self.name}>"
