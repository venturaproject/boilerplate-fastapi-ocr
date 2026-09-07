import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.permission import Permission


async def list_permissions(db: AsyncSession) -> list[Permission]:
    result = await db.execute(select(Permission).order_by(Permission.name))
    return list(result.scalars().all())


async def get_permission_by_id(db: AsyncSession, perm_id: uuid.UUID) -> Permission | None:
    result = await db.execute(select(Permission).where(Permission.id == perm_id))
    return result.scalar_one_or_none()


async def get_permission_by_name(db: AsyncSession, name: str) -> Permission | None:
    result = await db.execute(select(Permission).where(Permission.name == name))
    return result.scalar_one_or_none()


async def get_or_create_permission(db: AsyncSession, name: str, guard_name: str = "api") -> Permission:
    perm = await get_permission_by_name(db, name)
    if perm:
        return perm
    perm = Permission(name=name, guard_name=guard_name)
    db.add(perm)
    await db.flush()
    return perm
