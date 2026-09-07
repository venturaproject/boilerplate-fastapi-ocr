import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Trabajador(Base):
    __tablename__ = "trabajadores"

    ESTADO_ACTIVO = "activo"
    ESTADO_INACTIVO = "inactivo"
    ESTADO_BAJA = "baja"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(255))
    apellido: Mapped[str] = mapped_column(String(255), default="")
    synergy_res_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True)
    dni: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(50), nullable=True)
    estado: Mapped[str] = mapped_column(String(20), default="activo")
    emp_stat: Mapped[str | None] = mapped_column(String(50), nullable=True)
    cargo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    departamento: Mapped[str | None] = mapped_column(String(255), nullable=True)
    loc: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ubicacion: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ciudad: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fecha_incorporacion: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_baja: Mapped[date | None] = mapped_column(Date, nullable=True)
    observaciones: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    telefonos: Mapped[list["Telefono"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Telefono", back_populates="trabajador", lazy="selectin"
    )
    dispositivos: Mapped[list["Dispositivo"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Dispositivo", back_populates="trabajador", lazy="selectin"
    )

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombre} {self.apellido}".strip()

    def __repr__(self) -> str:
        return f"<Trabajador {self.nombre_completo}>"
