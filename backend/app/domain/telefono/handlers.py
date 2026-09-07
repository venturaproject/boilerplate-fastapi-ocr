from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.cqrs import command_handler, query_handler
from app.repositories import telefono as repo

from .commands import CreateTelefono, DeleteTelefono, UpdateTelefono
from .queries import GetTelefono, ListTelefonos


@command_handler(CreateTelefono)
async def handle_create(session: AsyncSession, cmd: CreateTelefono) -> uuid.UUID:
    t = await repo.create_telefono(session, cmd.data)
    return t.id


@command_handler(UpdateTelefono)
async def handle_update(session: AsyncSession, cmd: UpdateTelefono) -> uuid.UUID | None:
    t = await repo.get_telefono_by_id(session, cmd.id)
    if t is None:
        return None
    await repo.update_telefono(session, t, cmd.data)
    return t.id


@command_handler(DeleteTelefono)
async def handle_delete(session: AsyncSession, cmd: DeleteTelefono) -> bool:
    t = await repo.get_telefono_by_id(session, cmd.id)
    if t is None:
        return False
    await repo.delete_telefono(session, t)
    return True


@query_handler(ListTelefonos)
async def handle_list(session: AsyncSession, q: ListTelefonos):
    return await repo.list_telefonos(
        session,
        page=q.page,
        per_page=q.per_page,
        search=q.search,
        activo=q.activo,
        estado_id=q.estado_id,
        trabajador_id=q.trabajador_id,
    )


@query_handler(GetTelefono)
async def handle_get(session: AsyncSession, q: GetTelefono):
    return await repo.get_telefono_by_id(session, q.id)
