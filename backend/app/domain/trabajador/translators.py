from __future__ import annotations

from app.cqrs import Command
from app.events import inbox_translator

from .commands import SyncTrabajadorFromERP

_KNOWN = {
    "synergy_res_id",
    "nombre_completo",
    "email",
    "estado",
    "emp_stat",
    "loc",
    "ubicacion",
    "ciudad",
}


@inbox_translator("synergy", "employee.upserted")
def employee_upserted(payload: dict) -> Command:
    known = {k: v for k, v in payload.items() if k in _KNOWN}
    extra = {k: v for k, v in payload.items() if k not in _KNOWN and k not in ("id", "event")}
    return SyncTrabajadorFromERP(**known, extra=extra)
