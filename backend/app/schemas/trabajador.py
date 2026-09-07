import uuid
from datetime import date, datetime

from pydantic import BaseModel


class TrabajadorOut(BaseModel):
    id: uuid.UUID
    nombre: str
    apellido: str = ""
    nombre_completo: str
    synergy_res_id: int | None = None
    dni: str | None = None
    email: str | None = None
    telefono: str | None = None
    telefono_synergy: str | None = None
    estado: str
    activo: bool = True
    emp_stat: str | None = None
    cargo: str | None = None
    departamento: str | None = None
    loc: str | None = None
    ubicacion: str | None = None
    ciudad: str | None = None
    imei: str | None = None
    fecha_incorporacion: date | None = None
    fecha_alta: date | None = None
    fecha_baja: date | None = None
    observaciones: str = ""
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def model_validate(cls, obj, **kwargs):
        instance = super().model_validate(obj, **kwargs)
        if hasattr(obj, "nombre_completo"):
            instance.nombre_completo = obj.nombre_completo
        return instance


class TrabajadorListResponse(BaseModel):
    data: list[TrabajadorOut]
    current_page: int
    last_page: int
    per_page: int
    total: int


class CreateTrabajadorRequest(BaseModel):
    nombre: str
    apellido: str = ""
    dni: str | None = None
    email: str | None = None
    telefono: str | None = None
    estado: str = "activo"
    cargo: str | None = None
    departamento: str | None = None
    loc: str | None = None
    ubicacion: str | None = None
    ciudad: str | None = None
    fecha_incorporacion: date | None = None
    observaciones: str = ""


class UpdateTrabajadorRequest(BaseModel):
    nombre: str | None = None
    apellido: str | None = None
    dni: str | None = None
    email: str | None = None
    telefono: str | None = None
    estado: str | None = None
    cargo: str | None = None
    departamento: str | None = None
    loc: str | None = None
    ubicacion: str | None = None
    ciudad: str | None = None
    fecha_incorporacion: date | None = None
    fecha_baja: date | None = None
    observaciones: str | None = None
