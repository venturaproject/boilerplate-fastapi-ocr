from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.cqrs import command_handler, query_handler
from app.repositories import dispositivo as repo

from .commands import CreateDispositivo, DeleteDispositivo, UpdateDispositivo
from .queries import GetDispositivo, ListDispositivos


@command_handler(CreateDispositivo)
async def handle_create(session: AsyncSession, cmd: CreateDispositivo) -> uuid.UUID:
    d = await repo.create_dispositivo(session, cmd.data)
    return d.id


@command_handler(UpdateDispositivo)
async def handle_update(session: AsyncSession, cmd: UpdateDispositivo) -> uuid.UUID | None:
    d = await repo.get_dispositivo_by_id(session, cmd.id)
    if d is None:
        return None
    await repo.update_dispositivo(session, d, cmd.data)
    return d.id


@command_handler(DeleteDispositivo)
async def handle_delete(session: AsyncSession, cmd: DeleteDispositivo) -> bool:
    d = await repo.get_dispositivo_by_id(session, cmd.id)
    if d is None:
        return False
    await repo.delete_dispositivo(session, d)
    return True


@query_handler(ListDispositivos)
async def handle_list(session: AsyncSession, q: ListDispositivos):
    return await repo.list_dispositivos(
        session,
        page=q.page,
        per_page=q.per_page,
        search=q.search,
        estado=q.estado,
        trabajador_id=q.trabajador_id,
    )


@query_handler(GetDispositivo)
async def handle_get(session: AsyncSession, q: GetDispositivo):
    return await repo.get_dispositivo_by_id(session, q.id)
