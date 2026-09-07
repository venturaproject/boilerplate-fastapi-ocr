from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import ExtClientContext, require_scope
from app.events.inbox import store
from app.ratelimit import rate_limit

router = APIRouter(prefix="/api/ext/webhooks", tags=["webhooks"])

_wh_limit, _wh_per = settings.throttle(settings.throttle_webhook)

SOURCE = "synergy"


@router.post("/synergy", dependencies=[Depends(rate_limit("webhook", _wh_limit, _wh_per))])
async def synergy_webhook(
    response: Response,
    payload: dict[str, Any] = Body(...),
    x_message_id: str | None = Header(default=None),
    ctx: ExtClientContext = require_scope("webhooks:write"),
    db: AsyncSession = Depends(get_db),
):
    """Recibe eventos del ERP Synergy. Almacena el mensaje en el inbox de forma
    idempotente (`X-Message-Id`) y responde rápido; el procesado real lo hace
    `app.events.worker` / `process_inbox_batch`."""
    message_id = x_message_id or str(payload.get("id") or "")
    if not message_id:
        raise HTTPException(status_code=400, detail="Falta X-Message-Id (o 'id' en el cuerpo).")

    event_name = payload.get("event") or payload.get("event_name") or ""
    if not event_name:
        raise HTTPException(status_code=400, detail="Falta 'event' en el cuerpo.")

    _, created = await store(
        db, source=SOURCE, message_id=message_id, event_name=event_name, payload=payload
    )
    if created:
        response.status_code = 202
        return {"status": "accepted", "message_id": message_id}
    return {"status": "duplicate", "message_id": message_id}
