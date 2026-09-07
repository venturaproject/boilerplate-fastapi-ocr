import math
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.cqrs import command_bus, query_bus
from app.database import get_db
from app.dependencies import require_permission
from app.domain.dispositivo.commands import CreateDispositivo, DeleteDispositivo, UpdateDispositivo
from app.domain.dispositivo.queries import GetDispositivo, ListDispositivos
from app.exceptions import NotFoundException
from app.repositories import dispositivo as dispositivo_repo
from app.schemas.dispositivo import (
    CreateDispositivoRequest,
    DispositivoListResponse,
    DispositivoOut,
    UpdateDispositivoRequest,
)

router = APIRouter(prefix="/api/v1/dispositivos", tags=["dispositivos"])


@router.get("", dependencies=[require_permission("dispositivos.view")])
async def list_dispositivos(
    page: int = 1,
    per_page: int = 20,
    search: str | None = None,
    estado: str | None = None,
    trabajador_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    items, total = await query_bus.ask(
        db,
        ListDispositivos(
            page=page, per_page=per_page, search=search, estado=estado, trabajador_id=trabajador_id
        ),
    )
    last_page = max(1, math.ceil(total / per_page))
    return DispositivoListResponse(
        data=[DispositivoOut.model_validate(d) for d in items],
        current_page=page,
        last_page=last_page,
        per_page=per_page,
        total=total,
    )


@router.post("", dependencies=[require_permission("dispositivos.create")], status_code=201)
async def create_dispositivo(body: CreateDispositivoRequest, db: AsyncSession = Depends(get_db)):
    new_id = await command_bus.dispatch(db, CreateDispositivo(data=body.model_dump()))
    d = await dispositivo_repo.get_dispositivo_by_id(db, new_id)
    return DispositivoOut.model_validate(d)


@router.get("/{dispositivo_id}", dependencies=[require_permission("dispositivos.view")])
async def get_dispositivo(dispositivo_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    d = await query_bus.ask(db, GetDispositivo(id=dispositivo_id))
    if not d:
        raise NotFoundException()
    return DispositivoOut.model_validate(d)


@router.patch("/{dispositivo_id}", dependencies=[require_permission("dispositivos.edit")])
async def update_dispositivo(
    dispositivo_id: uuid.UUID,
    body: UpdateDispositivoRequest,
    db: AsyncSession = Depends(get_db),
):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    updated_id = await command_bus.dispatch(db, UpdateDispositivo(id=dispositivo_id, data=data))
    if updated_id is None:
        raise NotFoundException()
    d = await dispositivo_repo.get_dispositivo_by_id(db, updated_id)
    return DispositivoOut.model_validate(d)


@router.delete("/{dispositivo_id}", dependencies=[require_permission("dispositivos.delete")], status_code=204)
async def delete_dispositivo(dispositivo_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    deleted = await command_bus.dispatch(db, DeleteDispositivo(id=dispositivo_id))
    if not deleted:
        raise NotFoundException()
