import math
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.exceptions import ConflictException, NotFoundException
from app.repositories import user as user_repo
from app.repositories.role import list_roles
from app.schemas.user import (
    CreateUserRequest,
    RoleSimple,
    UpdateUserRequest,
    UserListResponse,
    UserOut,
    UserStatsOut,
)
from app.services.password import hash_password

router = APIRouter(prefix="/api/v1/users", tags=["users"])


def _user_out(user) -> UserOut:
    permissions = user.permission_names
    roles = [RoleSimple(id=r.id, name=r.name) for r in user.roles]
    avatar = user.settings.avatar if user.settings else None
    from app.schemas.user import UserSettingsOut
    user_settings = UserSettingsOut.model_validate(user.settings) if user.settings else None
    return UserOut(
        id=user.id,
        name=user.name,
        username=user.username,
        email=user.email,
        status=user.status,
        roles=roles,
        permissions=permissions,
        avatar=avatar,
        created_at=user.created_at,
        settings=user_settings,
    )


@router.get("", dependencies=[require_permission("users.view")])
async def list_users(
    page: int = 1,
    per_page: int = 20,
    search: str | None = None,
    status: str | None = None,
    role: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    users, total = await user_repo.list_users(db, page=page, per_page=per_page, search=search, status=status, role=role)
    stats = await user_repo.count_users_by_status(db)
    all_roles, _ = await list_roles(db, per_page=1000)
    last_page = max(1, math.ceil(total / per_page))

    return UserListResponse(
        data=[_user_out(u) for u in users],
        current_page=page,
        last_page=last_page,
        per_page=per_page,
        total=total,
        stats=UserStatsOut(**stats),
        roles=[RoleSimple(id=r.id, name=r.name) for r in all_roles],
    )


@router.post("", dependencies=[require_permission("users.create")], status_code=201)
async def create_user(
    body: CreateUserRequest,
    db: AsyncSession = Depends(get_db),
):
    existing = await user_repo.get_user_by_email(db, body.email)
    if existing:
        raise ConflictException(detail="Ya existe un usuario con ese email")

    user = await user_repo.create_user(
        db,
        name=body.name,
        email=body.email,
        password_hash=hash_password(body.password),
        username=body.username,
        status=body.status,
        role_ids=body.role_ids,
    )
    return _user_out(user)


@router.get("/{user_id}", dependencies=[require_permission("users.view")])
async def get_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    user = await user_repo.get_user_by_id(db, user_id)
    if not user:
        raise NotFoundException()
    return _user_out(user)


@router.patch("/{user_id}", dependencies=[require_permission("users.edit")])
async def update_user(
    user_id: uuid.UUID,
    body: UpdateUserRequest,
    db: AsyncSession = Depends(get_db),
):
    user = await user_repo.get_user_by_id(db, user_id)
    if not user:
        raise NotFoundException()

    update_kwargs: dict = {}
    if body.name is not None:
        update_kwargs["name"] = body.name
    if body.email is not None:
        existing = await user_repo.get_user_by_email(db, body.email)
        if existing and existing.id != user_id:
            raise ConflictException(detail="Ya existe un usuario con ese email")
        update_kwargs["email"] = body.email
    if body.password is not None:
        update_kwargs["password_hash"] = hash_password(body.password)
    if body.username is not None:
        update_kwargs["username"] = body.username
    if body.status is not None:
        update_kwargs["status"] = body.status
    if body.role_ids is not None:
        update_kwargs["role_ids"] = body.role_ids

    updated = await user_repo.update_user(db, user, **update_kwargs)
    return _user_out(updated)


@router.delete("/{user_id}", dependencies=[require_permission("users.delete")], status_code=204)
async def delete_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    user = await user_repo.get_user_by_id(db, user_id)
    if not user:
        raise NotFoundException()
    await user_repo.delete_user(db, user)
