from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.audit import AuditEvent

logger = logging.getLogger("app.audit")


async def record(
    *,
    action: str,
    actor_type: str = "system",
    actor_id: uuid.UUID | None = None,
    actor_label: str | None = None,
    target: str | None = None,
    ip: str | None = None,
    meta: dict[str, Any] | None = None,
) -> None:
    """Append an audit event in its own transaction. Never raises."""
    try:
        async with AsyncSessionLocal() as db, db.begin():
            db.add(
                AuditEvent(
                    action=action,
                    actor_type=actor_type,
                    actor_id=actor_id,
                    actor_label=(actor_label or "")[:255] or None,
                    target=(target or "")[:255] or None,
                    ip=(ip or "")[:64] or None,
                    meta=meta,
                )
            )
    except Exception:
        logger.exception("No se pudo registrar el evento de auditoría %s", action)


async def list_events(
    db: AsyncSession,
    *,
    action: str | None = None,
    actor_label: str | None = None,
    page: int = 1,
    per_page: int = 50,
) -> tuple[list[AuditEvent], int]:
    from sqlalchemy import func

    filters = []
    if action:
        filters.append(AuditEvent.action == action)
    if actor_label:
        filters.append(AuditEvent.actor_label.ilike(f"%{actor_label}%"))

    total = (await db.execute(select(func.count()).select_from(AuditEvent).where(*filters))).scalar_one()
    rows = (
        (
            await db.execute(
                select(AuditEvent)
                .where(*filters)
                .order_by(AuditEvent.created_at.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
            )
        )
        .scalars()
        .all()
    )
    return list(rows), total
