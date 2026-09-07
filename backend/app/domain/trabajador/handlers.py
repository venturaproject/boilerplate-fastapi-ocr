"""Command/query handlers de `trabajador`. Los importa `app.domain` al arranque.

Handlers finos: llaman a `app/repositories/trabajador.py` sin reescribir lógica.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.cqrs import command_handler, query_handler
from app.events import record_events
from app.repositories import trabajador as repo

from .commands import CreateTrabajador, DeleteTrabajador, SyncTrabajadorFromERP, UpdateTrabajador
from .events import TrabajadorSynchronizedFromERP
from .queries import GetTrabajador, ListTrabajadores

_ERP_FIELDS = ("email", "estado", "emp_stat", "loc", "ubicacion", "ciudad")


@command_handler(CreateTrabajador)
async def handle_create(session: AsyncSession, cmd: CreateTrabajador) -> uuid.UUID:
    t = await repo.create_trabajador(session, cmd.data)
    return t.id


@command_handler(UpdateTrabajador)
async def handle_update(session: AsyncSession, cmd: UpdateTrabajador) -> uuid.UUID | None:
    t = await repo.get_trabajador_by_id(session, cmd.id)
    if t is None:
        return None
    await repo.update_trabajador(session, t, cmd.data)
    return t.id


@command_handler(DeleteTrabajador)
async def handle_delete(session: AsyncSession, cmd: DeleteTrabajador) -> bool:
    t = await repo.get_trabajador_by_id(session, cmd.id)
    if t is None:
        return False
    await repo.delete_trabajador(session, t)
    return True


@command_handler(SyncTrabajadorFromERP)
async def handle_sync_from_erp(session: AsyncSession, cmd: SyncTrabajadorFromERP) -> uuid.UUID:
    existing = (
        await repo.get_by_synergy_res_id(session, cmd.synergy_res_id)
        if cmd.synergy_res_id is not None
        else None
    )
    fields = {f: getattr(cmd, f) for f in _ERP_FIELDS if getattr(cmd, f) is not None}

    if existing is not None:
        await repo.update_trabajador(session, existing, fields)
        t, created = existing, False
    else:
        parts = cmd.nombre_completo.split(" ", 1)
        t = await repo.create_trabajador(
            session,
            {
                "nombre": parts[0] or "",
                "apellido": parts[1] if len(parts) > 1 else "",
                "synergy_res_id": cmd.synergy_res_id,
                **fields,
            },
        )
        created = True

    record_events([
        TrabajadorSynchronizedFromERP(
            aggregate_id=str(t.id),
            aggregate_type="Trabajador",
            synergy_res_id=t.synergy_res_id,
            created=created,
        )
    ])
    return t.id


@query_handler(ListTrabajadores)
async def handle_list(session: AsyncSession, q: ListTrabajadores):
    return await repo.list_trabajadores(
        session,
        page=q.page,
        per_page=q.per_page,
        search=q.search,
        estado=q.estado,
        departamento=q.departamento,
    )


@query_handler(GetTrabajador)
async def handle_get(session: AsyncSession, q: GetTrabajador):
    return await repo.get_trabajador_by_id(session, q.id)
