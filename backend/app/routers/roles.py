import math
import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import log as audit_log
from app.database import get_db
from app.dependencies import require_permission
from app.exceptions import ConflictException, NotFoundException
from app.models.user import User
from app.repositories import role as role_repo
from app.schemas.role import CreateRoleRequest, RoleListResponse, RoleOut, UpdateRoleRequest

router = APIRouter(prefix="/api/v1/roles", tags=["roles"])


@router.get("", dependencies=[require_permission("roles.view")])
async def list_roles(
    page: int = 1,
    per_page: int = 20,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> RoleListResponse:
    per_page = max(1, min(per_page, 1000))
    page = max(1, page)
    roles, total = await role_repo.list_roles(db, search=search, page=page, per_page=per_page)
    return RoleListResponse(
        data=[RoleOut.model_validate(r) for r in roles],
        current_page=page,
        last_page=max(1, math.ceil(total / per_page)),
        per_page=per_page,
        total=total,
    )


@router.post("", status_code=201)
async def create_role(
    body: CreateRoleRequest,
    request: Request,
    actor: User = require_permission("roles.create"),
    db: AsyncSession = Depends(get_db),
) -> RoleOut:
    existing = await role_repo.get_role_by_name(db, body.name)
    if existing:
        raise ConflictException(detail="Ya existe un rol con ese nombre")
    role = await role_repo.create_role(
        db, name=body.name, guard_name=body.guard_name, permission_ids=body.permission_ids
    )
    await audit_log(request, actor, "role.created", role.name, permissions=body.permission_ids)
    return RoleOut.model_validate(role)


@router.get("/{role_id}", dependencies=[require_permission("roles.view")])
async def get_role(role_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> RoleOut:
    role = await role_repo.get_role_by_id(db, role_id)
    if not role:
        raise NotFoundException()
    return RoleOut.model_validate(role)


@router.patch("/{role_id}")
async def update_role(
    role_id: uuid.UUID,
    body: UpdateRoleRequest,
    request: Request,
    actor: User = require_permission("roles.edit"),
    db: AsyncSession = Depends(get_db),
) -> RoleOut:
    role = await role_repo.get_role_by_id(db, role_id)
    if not role:
        raise NotFoundException()
    updated = await role_repo.update_role(db, role, name=body.name, permission_ids=body.permission_ids)
    await audit_log(request, actor, "role.updated", updated.name, permissions=body.permission_ids)
    return RoleOut.model_validate(updated)


@router.delete("/{role_id}", status_code=204)
async def delete_role(
    role_id: uuid.UUID,
    request: Request,
    actor: User = require_permission("roles.delete"),
    db: AsyncSession = Depends(get_db),
) -> None:
    role = await role_repo.get_role_by_id(db, role_id)
    if not role:
        raise NotFoundException()
    await role_repo.delete_role(db, role)
    await audit_log(request, actor, "role.deleted", role.name)
