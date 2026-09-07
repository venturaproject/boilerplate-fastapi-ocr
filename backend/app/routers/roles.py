import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.exceptions import ConflictException, NotFoundException
from app.repositories import role as role_repo
from app.schemas.role import CreateRoleRequest, RoleOut, UpdateRoleRequest

router = APIRouter(prefix="/api/v1/roles", tags=["roles"])


@router.get("", dependencies=[require_permission("roles.view")])
async def list_roles(db: AsyncSession = Depends(get_db)):
    roles = await role_repo.list_roles(db)
    return [RoleOut.model_validate(r) for r in roles]


@router.post("", dependencies=[require_permission("roles.create")], status_code=201)
async def create_role(body: CreateRoleRequest, db: AsyncSession = Depends(get_db)):
    existing = await role_repo.get_role_by_name(db, body.name)
    if existing:
        raise ConflictException(detail="Ya existe un rol con ese nombre")
    role = await role_repo.create_role(db, name=body.name, guard_name=body.guard_name, permission_ids=body.permission_ids)
    return RoleOut.model_validate(role)


@router.get("/{role_id}", dependencies=[require_permission("roles.view")])
async def get_role(role_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    role = await role_repo.get_role_by_id(db, role_id)
    if not role:
        raise NotFoundException()
    return RoleOut.model_validate(role)


@router.patch("/{role_id}", dependencies=[require_permission("roles.edit")])
async def update_role(role_id: uuid.UUID, body: UpdateRoleRequest, db: AsyncSession = Depends(get_db)):
    role = await role_repo.get_role_by_id(db, role_id)
    if not role:
        raise NotFoundException()
    updated = await role_repo.update_role(db, role, name=body.name, permission_ids=body.permission_ids)
    return RoleOut.model_validate(updated)


@router.delete("/{role_id}", dependencies=[require_permission("roles.delete")], status_code=204)
async def delete_role(role_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    role = await role_repo.get_role_by_id(db, role_id)
    if not role:
        raise NotFoundException()
    await role_repo.delete_role(db, role)
