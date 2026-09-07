import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, model_validator


class MarcaSimple(BaseModel):
    id: uuid.UUID
    nombre: str

    model_config = {"from_attributes": True}


class ModeloSimple(BaseModel):
    id: uuid.UUID
    nombre: str

    model_config = {"from_attributes": True}


class TrabajadorSimple(BaseModel):
    id: uuid.UUID
    nombre: str
    apellido: str = ""

    model_config = {"from_attributes": True}


class DeviceEmployeeOut(BaseModel):
    id: uuid.UUID
    nombre_completo: str
    email: str | None = None

    model_config = {"from_attributes": True}


class DispositivoOut(BaseModel):
    id: uuid.UUID
    numero: str | None = None
    imei: str | None = None
    serie: str | None = None
    synergy_res_id: int | None = None
    marca_id: uuid.UUID | None = None
    modelo_id: uuid.UUID | None = None
    marca: str | None = None
    modelo: str | None = None
    grupo: str | None = None
    estado: str
    employee: DeviceEmployeeOut | None = None
    observaciones: str = ""
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def flatten_relations(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return data

        employee = None
        if data.trabajador:
            nc = f"{data.trabajador.nombre} {data.trabajador.apellido}".strip()
            employee = {"id": data.trabajador.id, "nombre_completo": nc, "email": None}

        return {
            "id": data.id,
            "numero": data.numero,
            "imei": data.imei,
            "serie": data.serie,
            "synergy_res_id": data.synergy_res_id,
            "marca_id": data.marca_id,
            "modelo_id": data.modelo_id,
            "marca": data.marca.nombre if data.marca else None,
            "modelo": data.modelo.nombre if data.modelo else None,
            "grupo": data.grupo,
            "estado": data.estado,
            "employee": employee,
            "observaciones": data.observaciones,
            "created_at": data.created_at,
            "updated_at": data.updated_at,
        }


class DispositivoListResponse(BaseModel):
    data: list[DispositivoOut]
    current_page: int
    last_page: int
    per_page: int
    total: int


class CreateDispositivoRequest(BaseModel):
    numero: str | None = None
    imei: str | None = None
    serie: str | None = None
    marca_id: uuid.UUID | None = None
    modelo_id: uuid.UUID | None = None
    grupo: str | None = None
    estado: str = "disponible"
    trabajador_id: uuid.UUID | None = None
    observaciones: str = ""


class UpdateDispositivoRequest(BaseModel):
    numero: str | None = None
    imei: str | None = None
    serie: str | None = None
    marca_id: uuid.UUID | None = None
    modelo_id: uuid.UUID | None = None
    grupo: str | None = None
    estado: str | None = None
    trabajador_id: uuid.UUID | None = None
    observaciones: str | None = None
