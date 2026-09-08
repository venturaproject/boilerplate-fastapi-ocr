import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.repositories import audit as audit_repo

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


class AuditEventOut(BaseModel):
    id: uuid.UUID
    created_at: datetime
    action: str
    actor_type: str
    actor_id: uuid.UUID | None = None
    actor_label: str | None = None
    target: str | None = None
    ip: str | None = None
    meta: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class AuditListResponse(BaseModel):
    data: list[AuditEventOut]
    total: int
    page: int
    per_page: int


@router.get("", dependencies=[require_permission("audit.view")])
async def list_audit_events(
    page: int = 1,
    per_page: int = 50,
    action: str | None = None,
    actor: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> AuditListResponse:
    per_page = max(1, min(per_page, 200))
    page = max(1, page)
    rows, total = await audit_repo.list_events(db, action=action, actor_label=actor, page=page, per_page=per_page)
    return AuditListResponse(
        data=[AuditEventOut.model_validate(r) for r in rows],
        total=total,
        page=page,
        per_page=per_page,
    )
