import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DeviceBrand(Base):
    __tablename__ = "device_brands"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(100), unique=True)

    modelos: Mapped[list["DeviceModel"]] = relationship("DeviceModel", back_populates="marca", lazy="selectin")
    dispositivos: Mapped[list["Dispositivo"]] = relationship("Dispositivo", back_populates="marca", lazy="selectin")

    def __repr__(self) -> str:
        return f"<DeviceBrand {self.nombre}>"


class DeviceModel(Base):
    __tablename__ = "device_models"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(100))
    marca_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("device_brands.id", ondelete="CASCADE"))

    marca: Mapped["DeviceBrand"] = relationship("DeviceBrand", back_populates="modelos", lazy="selectin")
    dispositivos: Mapped[list["Dispositivo"]] = relationship("Dispositivo", back_populates="modelo", lazy="selectin")

    def __repr__(self) -> str:
        return f"<DeviceModel {self.nombre}>"


class Dispositivo(Base):
    __tablename__ = "dispositivos"

    ESTADO_DISPONIBLE = "disponible"
    ESTADO_ASIGNADO = "asignado"
    ESTADO_BAJA = "baja"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    numero: Mapped[str | None] = mapped_column(String(100), nullable=True)
    imei: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    serie: Mapped[str | None] = mapped_column(String(100), nullable=True)
    synergy_res_id: Mapped[int | None] = mapped_column(unique=True, nullable=True)
    marca_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("device_brands.id", ondelete="SET NULL"), nullable=True
    )
    modelo_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("device_models.id", ondelete="SET NULL"), nullable=True
    )
    grupo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    estado: Mapped[str] = mapped_column(String(20), default="disponible")
    trabajador_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("trabajadores.id", ondelete="SET NULL"), nullable=True
    )
    observaciones: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    marca: Mapped["DeviceBrand | None"] = relationship("DeviceBrand", back_populates="dispositivos", lazy="selectin")
    modelo: Mapped["DeviceModel | None"] = relationship("DeviceModel", back_populates="dispositivos", lazy="selectin")
    trabajador: Mapped["Trabajador | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Trabajador", back_populates="dispositivos", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Dispositivo {self.numero or self.serie}>"
