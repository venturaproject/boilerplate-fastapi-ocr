import math
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.cqrs import command_bus, query_bus
from app.database import get_db
from app.dependencies import require_permission
from app.domain.telefono.commands import CreateTelefono, DeleteTelefono, UpdateTelefono
from app.domain.telefono.queries import GetTelefono, ListTelefonos
from app.exceptions import NotFoundException
from app.repositories import telefono as telefono_repo
from app.schemas.telefono import (
    CreateTelefonoRequest,
    EstadoTelefonoOut,
    TelefonoListResponse,
    TelefonoOut,
    TipologiaOut,
    UpdateTelefonoRequest,
)

router = APIRouter(prefix="/api/v1/telefonos", tags=["telefonos"])


@router.get("/estados", dependencies=[require_permission("telefonos.view")])
async def list_estados(db: AsyncSession = Depends(get_db)):
    estados = await telefono_repo.list_estados(db)
    return [EstadoTelefonoOut.model_validate(e) for e in estados]


@router.get("/tipologias", dependencies=[require_permission("telefonos.view")])
async def list_tipologias(db: AsyncSession = Depends(get_db)):
    tipologias = await telefono_repo.list_tipologias(db)
    return [TipologiaOut.model_validate(t) for t in tipologias]


@router.get("", dependencies=[require_permission("telefonos.view")])
async def list_telefonos(
    page: int = 1,
    per_page: int = 20,
    search: str | None = None,
    activo: bool | None = None,
    estado_id: uuid.UUID | None = None,
    trabajador_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    items, total = await query_bus.ask(
        db,
        ListTelefonos(
            page=page,
            per_page=per_page,
            search=search,
            activo=activo,
            estado_id=estado_id,
            trabajador_id=trabajador_id,
        ),
    )
    last_page = max(1, math.ceil(total / per_page))
    return TelefonoListResponse(
        data=[TelefonoOut.model_validate(t) for t in items],
        current_page=page,
        last_page=last_page,
        per_page=per_page,
        total=total,
    )


@router.post("", dependencies=[require_permission("telefonos.create")], status_code=201)
async def create_telefono(body: CreateTelefonoRequest, db: AsyncSession = Depends(get_db)):
    new_id = await command_bus.dispatch(db, CreateTelefono(data=body.model_dump()))
    t = await telefono_repo.get_telefono_by_id(db, new_id)
    return TelefonoOut.model_validate(t)


@router.get("/{telefono_id}", dependencies=[require_permission("telefonos.view")])
async def get_telefono(telefono_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    t = await query_bus.ask(db, GetTelefono(id=telefono_id))
    if not t:
        raise NotFoundException()
    return TelefonoOut.model_validate(t)


@router.patch("/{telefono_id}", dependencies=[require_permission("telefonos.edit")])
async def update_telefono(
    telefono_id: uuid.UUID,
    body: UpdateTelefonoRequest,
    db: AsyncSession = Depends(get_db),
):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    updated_id = await command_bus.dispatch(db, UpdateTelefono(id=telefono_id, data=data))
    if updated_id is None:
        raise NotFoundException()
    t = await telefono_repo.get_telefono_by_id(db, updated_id)
    return TelefonoOut.model_validate(t)


@router.delete("/{telefono_id}", dependencies=[require_permission("telefonos.delete")], status_code=204)
async def delete_telefono(telefono_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    deleted = await command_bus.dispatch(db, DeleteTelefono(id=telefono_id))
    if not deleted:
        raise NotFoundException()
