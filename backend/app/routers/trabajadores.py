import math
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.cqrs import command_bus, query_bus
from app.database import get_db
from app.dependencies import require_permission
from app.domain.trabajador.commands import CreateTrabajador, DeleteTrabajador, UpdateTrabajador
from app.domain.trabajador.queries import GetTrabajador, ListTrabajadores
from app.exceptions import NotFoundException
from app.repositories import trabajador as trabajador_repo
from app.schemas.trabajador import (
    CreateTrabajadorRequest,
    TrabajadorListResponse,
    TrabajadorOut,
    UpdateTrabajadorRequest,
)

router = APIRouter(prefix="/api/v1/trabajadores", tags=["trabajadores"])


def _to_out(t) -> TrabajadorOut:
    return TrabajadorOut(
        id=t.id,
        nombre=t.nombre,
        apellido=t.apellido,
        nombre_completo=t.nombre_completo,
        synergy_res_id=t.synergy_res_id,
        dni=t.dni,
        email=t.email,
        telefono=t.telefono,
        telefono_synergy=t.telefono,
        estado=t.estado,
        activo=(t.estado == "activo"),
        emp_stat=t.emp_stat,
        cargo=t.cargo,
        departamento=t.departamento,
        loc=t.loc,
        ubicacion=t.ubicacion,
        ciudad=t.ciudad,
        imei=None,
        fecha_incorporacion=t.fecha_incorporacion,
        fecha_alta=t.fecha_incorporacion,
        fecha_baja=t.fecha_baja,
        observaciones=t.observaciones,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


@router.get("", dependencies=[require_permission("trabajadores.view")])
async def list_trabajadores(
    page: int = 1,
    per_page: int = 20,
    search: str | None = None,
    estado: str | None = None,
    departamento: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    items, total = await query_bus.ask(
        db,
        ListTrabajadores(
            page=page, per_page=per_page, search=search, estado=estado, departamento=departamento
        ),
    )
    last_page = max(1, math.ceil(total / per_page))
    return TrabajadorListResponse(
        data=[_to_out(t) for t in items],
        current_page=page,
        last_page=last_page,
        per_page=per_page,
        total=total,
    )


@router.post("", dependencies=[require_permission("trabajadores.create")], status_code=201)
async def create_trabajador(body: CreateTrabajadorRequest, db: AsyncSession = Depends(get_db)):
    data = body.model_dump(exclude_none=False)
    new_id = await command_bus.dispatch(db, CreateTrabajador(data=data))
    t = await trabajador_repo.get_trabajador_by_id(db, new_id)
    return _to_out(t)


@router.get("/{trabajador_id}", dependencies=[require_permission("trabajadores.view")])
async def get_trabajador(trabajador_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    t = await query_bus.ask(db, GetTrabajador(id=trabajador_id))
    if not t:
        raise NotFoundException()
    return _to_out(t)


@router.patch("/{trabajador_id}", dependencies=[require_permission("trabajadores.edit")])
async def update_trabajador(
    trabajador_id: uuid.UUID,
    body: UpdateTrabajadorRequest,
    db: AsyncSession = Depends(get_db),
):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    updated_id = await command_bus.dispatch(db, UpdateTrabajador(id=trabajador_id, data=data))
    if updated_id is None:
        raise NotFoundException()
    t = await trabajador_repo.get_trabajador_by_id(db, updated_id)
    return _to_out(t)


@router.delete("/{trabajador_id}", dependencies=[require_permission("trabajadores.delete")], status_code=204)
async def delete_trabajador(trabajador_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    deleted = await command_bus.dispatch(db, DeleteTrabajador(id=trabajador_id))
    if not deleted:
        raise NotFoundException()
