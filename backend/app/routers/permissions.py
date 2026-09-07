import math
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.exceptions import NotFoundException
from app.repositories import permission as perm_repo
from app.schemas.permission import PermissionListResponse, PermissionOut

router = APIRouter(prefix="/api/v1/permissions", tags=["permissions"])


@router.get("", dependencies=[require_permission("permissions.view")])
async def list_permissions(
    page: int = 1,
    per_page: int = 20,
    search: str | None = None,
    group: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> PermissionListResponse:
    per_page = max(1, min(per_page, 1000))
    page = max(1, page)
    perms, total = await perm_repo.list_permissions(
        db, search=search, group=group, page=page, per_page=per_page
    )
    return PermissionListResponse(
        data=[PermissionOut.model_validate(p) for p in perms],
        groups=await perm_repo.list_permission_groups(db),
        current_page=page,
        last_page=max(1, math.ceil(total / per_page)),
        per_page=per_page,
        total=total,
    )


@router.get("/{perm_id}", dependencies=[require_permission("permissions.view")])
async def get_permission(perm_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    perm = await perm_repo.get_permission_by_id(db, perm_id)
    if not perm:
        raise NotFoundException()
    return PermissionOut.model_validate(perm)
