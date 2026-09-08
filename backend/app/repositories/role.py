import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.permission import Permission
from app.models.role import Role


async def list_roles(
    db: AsyncSession,
    *,
    search: str | None = None,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[Role], int]:
    query = select(Role)
    if search:
        query = query.where(Role.name.ilike(f"%{search}%"))

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()

    result = await db.execute(
        query.options(selectinload(Role.permissions), selectinload(Role.users))
        .order_by(Role.name)
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    return list(result.scalars().all()), int(total)


async def get_role_by_id(db: AsyncSession, role_id: uuid.UUID) -> Role | None:
    result = await db.execute(select(Role).options(selectinload(Role.permissions)).where(Role.id == role_id))
    return result.scalar_one_or_none()


async def get_role_by_name(db: AsyncSession, name: str) -> Role | None:
    result = await db.execute(select(Role).where(Role.name == name))
    return result.scalar_one_or_none()


async def create_role(
    db: AsyncSession,
    name: str,
    guard_name: str = "api",
    permission_ids: list[uuid.UUID] | None = None,
) -> Role:
    role = Role(name=name, guard_name=guard_name)
    db.add(role)
    await db.flush()

    if permission_ids:
        result = await db.execute(select(Permission).where(Permission.id.in_(permission_ids)))
        perms = list(result.scalars().all())
        role.permissions = perms

    await db.flush()
    await db.refresh(role, ["permissions"])
    return role


async def update_role(
    db: AsyncSession,
    role: Role,
    name: str | None = None,
    permission_ids: list[uuid.UUID] | None = None,
) -> Role:
    if name is not None:
        role.name = name

    if permission_ids is not None:
        result = await db.execute(select(Permission).where(Permission.id.in_(permission_ids)))
        perms = list(result.scalars().all())
        role.permissions = perms

    await db.flush()
    await db.refresh(role, ["permissions"])
    return role


async def delete_role(db: AsyncSession, role: Role) -> None:
    await db.delete(role)
    await db.flush()
