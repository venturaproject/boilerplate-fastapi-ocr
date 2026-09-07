import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, model_validator

ESTADO_NAME_TO_INT: dict[str, int] = {
    "activo": 1,
    "congelado": 2,
    "baja": 3,
    "pendiente": 4,
    "sin datos": 5,
    "sin_datos": 5,
}


class EstadoTelefonoOut(BaseModel):
    id: uuid.UUID
    nombre: str
    color: str | None = None

    model_config = {"from_attributes": True}


class TipologiaOut(BaseModel):
    id: uuid.UUID
    nombre: str

    model_config = {"from_attributes": True}


class PhoneStatusOut(BaseModel):
    id: int
    nombre: str


class TelefonoTrabajadorOut(BaseModel):
    id: uuid.UUID
    nombre_completo: str
    telefono_synergy: str | None = None

    model_config = {"from_attributes": True}


class TelefonoOut(BaseModel):
    id: uuid.UUID
    telefono: str | None = None
    tipo: str | None = None
    plan: str | None = None
    nplan: str | None = None
    pin: str | None = None
    puk: str | None = None
    imei: str | None = None
    imei2: str | None = None
    marca: str | None = None
    modelo: str | None = None
    linea: str | None = None
    operadora: str | None = None
    estado_telefonos_id: int | None = None
    tipologias_id: int | None = None
    notas: str | None = None
    activo: bool = True
    status: PhoneStatusOut | None = None
    trabajador: TelefonoTrabajadorOut | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def flatten_relations(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return data

        estado_int = None
        status = None
        if data.estado:
            nombre_lower = data.estado.nombre.lower()
            estado_int = ESTADO_NAME_TO_INT.get(nombre_lower)
            status = {"id": estado_int or 0, "nombre": data.estado.nombre}

        trabajador = None
        if data.trabajador:
            nc = f"{data.trabajador.nombre} {data.trabajador.apellido}".strip()
            trabajador = {
                "id": data.trabajador.id,
                "nombre_completo": nc,
                "telefono_synergy": None,
            }

        return {
            "id": data.id,
            "telefono": data.numero,
            "tipo": data.tipo,
            "plan": data.plan,
            "nplan": data.nplan,
            "pin": data.pin,
            "puk": data.puk,
            "imei": data.imei,
            "imei2": data.imei2,
            "marca": data.marca,
            "modelo": data.modelo,
            "linea": data.linea,
            "operadora": data.operadora,
            "estado_telefonos_id": estado_int,
            "tipologias_id": None,
            "notas": data.observaciones,
            "activo": data.activo,
            "status": status,
            "trabajador": trabajador,
            "created_at": data.created_at,
            "updated_at": data.updated_at,
        }


class TelefonoListResponse(BaseModel):
    data: list[TelefonoOut]
    current_page: int
    last_page: int
    per_page: int
    total: int


class CreateTelefonoRequest(BaseModel):
    numero: str | None = None
    tipo: str | None = None
    plan: str | None = None
    nplan: str | None = None
    pin: str | None = None
    puk: str | None = None
    imei: str | None = None
    imei2: str | None = None
    marca: str | None = None
    modelo: str | None = None
    linea: str | None = None
    operadora: str | None = None
    estado_id: uuid.UUID | None = None
    tipologia_id: uuid.UUID | None = None
    trabajador_id: uuid.UUID | None = None
    observaciones: str = ""
    activo: bool = True


class UpdateTelefonoRequest(BaseModel):
    numero: str | None = None
    tipo: str | None = None
    plan: str | None = None
    nplan: str | None = None
    pin: str | None = None
    puk: str | None = None
    imei: str | None = None
    imei2: str | None = None
    marca: str | None = None
    modelo: str | None = None
    linea: str | None = None
    operadora: str | None = None
    estado_id: uuid.UUID | None = None
    tipologia_id: uuid.UUID | None = None
    trabajador_id: uuid.UUID | None = None
    observaciones: str | None = None
    activo: bool | None = None
