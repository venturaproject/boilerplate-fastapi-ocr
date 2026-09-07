import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.exceptions import NotFoundException
from app.repositories import permission as perm_repo
from app.schemas.permission import PermissionOut

router = APIRouter(prefix="/api/v1/permissions", tags=["permissions"])


@router.get("", dependencies=[require_permission("permissions.view")])
async def list_permissions(db: AsyncSession = Depends(get_db)):
    perms = await perm_repo.list_permissions(db)
    return [PermissionOut.model_validate(p) for p in perms]


@router.get("/{perm_id}", dependencies=[require_permission("permissions.view")])
async def get_permission(perm_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    perm = await perm_repo.get_permission_by_id(db, perm_id)
    if not perm:
        raise NotFoundException()
    return PermissionOut.model_validate(perm)
