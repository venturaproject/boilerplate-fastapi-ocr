import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.permission import Permission


async def list_permissions(
    db: AsyncSession,
    *,
    search: str | None = None,
    group: str | None = None,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[Permission], int]:
    query = select(Permission)
    if search:
        query = query.where(Permission.name.ilike(f"%{search}%"))
    if group:
        query = query.where(Permission.name.ilike(f"{group}.%"))

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()

    result = await db.execute(query.order_by(Permission.name).offset((page - 1) * per_page).limit(per_page))
    return list(result.scalars().all()), int(total)


async def list_permission_groups(db: AsyncSession) -> list[str]:
    """Distinct prefixes (`users`, `roles`, …) derived from `<group>.<action>` names."""
    names = (await db.execute(select(Permission.name))).scalars().all()
    return sorted({n.split(".")[0] for n in names if "." in n})


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
