"""Subscribers del event bus para eventos de `trabajador`.

Los ejecuta el worker cuando publica un mensaje del outbox. Punto de extensión:
notificaciones, side-effects, llamadas salientes, proyecciones…
"""

from __future__ import annotations

import logging

from app.events import subscribe

from .events import TrabajadorSynchronizedFromERP

logger = logging.getLogger("app.domain.trabajador")


@subscribe(TrabajadorSynchronizedFromERP.name())
async def log_trabajador_synced(payload: dict) -> None:
    action = "creado" if payload.get("created") else "actualizado"
    logger.info(
        "Trabajador %s desde Synergy (synergy_res_id=%s)",
        action,
        payload.get("synergy_res_id"),
    )


@subscribe(TrabajadorSynchronizedFromERP.name())
async def ack_synergy(payload: dict) -> None:
    # TODO: confirmar al ERP Synergy que el trabajador se sincronizó (POST a su API).
    logger.debug("ack Synergy pendiente para synergy_res_id=%s", payload.get("synergy_res_id"))
