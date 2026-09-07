import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EstadoTelefono(Base):
    __tablename__ = "estado_telefonos"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(100), unique=True)
    color: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    telefonos: Mapped[list["Telefono"]] = relationship("Telefono", back_populates="estado", lazy="selectin")

    def __repr__(self) -> str:
        return f"<EstadoTelefono {self.nombre}>"


class Tipologia(Base):
    __tablename__ = "tipologias"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(100), unique=True)

    telefonos: Mapped[list["Telefono"]] = relationship("Telefono", back_populates="tipologia", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Tipologia {self.nombre}>"


class Telefono(Base):
    __tablename__ = "telefonos"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    numero: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tipo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    plan: Mapped[str | None] = mapped_column(String(100), nullable=True)
    nplan: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pin: Mapped[str | None] = mapped_column(String(20), nullable=True)
    puk: Mapped[str | None] = mapped_column(String(20), nullable=True)
    imei: Mapped[str | None] = mapped_column(String(100), nullable=True)
    imei2: Mapped[str | None] = mapped_column(String(100), nullable=True)
    marca: Mapped[str | None] = mapped_column(String(100), nullable=True)
    modelo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    linea: Mapped[str | None] = mapped_column(String(100), nullable=True)
    operadora: Mapped[str | None] = mapped_column(String(100), nullable=True)
    estado_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("estado_telefonos.id", ondelete="SET NULL"), nullable=True
    )
    tipologia_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tipologias.id", ondelete="SET NULL"), nullable=True
    )
    trabajador_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("trabajadores.id", ondelete="SET NULL"), nullable=True
    )
    observaciones: Mapped[str] = mapped_column(Text, default="")
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    estado: Mapped["EstadoTelefono | None"] = relationship("EstadoTelefono", back_populates="telefonos", lazy="selectin")
    tipologia: Mapped["Tipologia | None"] = relationship("Tipologia", back_populates="telefonos", lazy="selectin")
    trabajador: Mapped["Trabajador | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Trabajador", back_populates="telefonos", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Telefono {self.numero or self.imei}>"
