"""Thin helper to log a panel action to the audit trail from a router."""

from __future__ import annotations

from fastapi import Request

from app.models.user import User
from app.repositories import audit as audit_repo


async def log(request: Request, actor: User, action: str, target: str | None = None, **meta: object) -> None:
    await audit_repo.record(
        action=action,
        actor_type="user",
        actor_id=actor.id,
        actor_label=actor.email,
        target=target,
        ip=request.client.host if request.client else None,
        meta=dict(meta) or None,
    )
