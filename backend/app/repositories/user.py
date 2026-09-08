import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models.role import Role
from app.models.user import User, UserSettings


async def note_failed_login(user_id: uuid.UUID, *, max_attempts: int, lockout_minutes: int) -> bool:
    """Bump the failed-login counter and lock the account once it reaches
    `max_attempts`. Runs in its own transaction (the login request rolls back on
    401). Returns True if the account is now locked."""
    if max_attempts <= 0:
        return False
    async with AsyncSessionLocal() as db, db.begin():
        attempts = (
            await db.execute(
                update(User)
                .where(User.id == user_id)
                .values(failed_login_attempts=User.failed_login_attempts + 1)
                .returning(User.failed_login_attempts)
            )
        ).scalar_one_or_none()
        if attempts is None or attempts < max_attempts:
            return False
        await db.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                failed_login_attempts=0,
                locked_until=datetime.now(tz=UTC) + timedelta(minutes=lockout_minutes),
            )
        )
    return True


async def clear_failed_logins(db: AsyncSession, user: User) -> None:
    user.failed_login_attempts = 0
    user.locked_until = None
    await db.flush()


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(
        select(User)
        .options(
            selectinload(User.roles).selectinload(Role.permissions),
            selectinload(User.settings),
        )
        .where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(
        select(User)
        .options(
            selectinload(User.roles).selectinload(Role.permissions),
            selectinload(User.settings),
        )
        .where(func.lower(User.email) == email.lower())
    )
    return result.scalar_one_or_none()


async def get_user_by_login(db: AsyncSession, login: str) -> User | None:
    result = await db.execute(
        select(User)
        .options(
            selectinload(User.roles).selectinload(Role.permissions),
            selectinload(User.settings),
        )
        .where(
            or_(
                func.lower(User.email) == login.lower(),
                func.lower(User.username) == login.lower(),
            )
        )
    )
    return result.scalar_one_or_none()


async def list_users(
    db: AsyncSession,
    page: int = 1,
    per_page: int = 20,
    search: str | None = None,
    status: str | None = None,
    role: str | None = None,
) -> tuple[list[User], int]:
    query = select(User).options(
        selectinload(User.roles).selectinload(Role.permissions),
        selectinload(User.settings),
    )

    if search:
        query = query.where(
            or_(
                User.name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.username.ilike(f"%{search}%"),
            )
        )

    if status:
        query = query.where(User.status == status)

    if role:
        query = query.join(User.roles).where(Role.name == role)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(User.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    users = list(result.scalars().all())

    return users, total


async def count_users_by_status(db: AsyncSession) -> dict[str, int]:
    result = await db.execute(select(func.count()).select_from(User))
    total = result.scalar_one()
    result_active = await db.execute(select(func.count()).select_from(User).where(User.status == "active"))
    activos = result_active.scalar_one()
    result_inactive = await db.execute(select(func.count()).select_from(User).where(User.status == "inactive"))
    inactivos = result_inactive.scalar_one()
    result_suspended = await db.execute(select(func.count()).select_from(User).where(User.status == "suspended"))
    suspendidos = result_suspended.scalar_one()
    return {"total": total, "activos": activos, "inactivos": inactivos, "suspendidos": suspendidos}


async def create_user(
    db: AsyncSession,
    name: str,
    email: str,
    password_hash: str,
    username: str | None = None,
    status: str = "active",
    role_ids: list[uuid.UUID] | None = None,
) -> User:
    user = User(
        name=name,
        email=email,
        password_hash=password_hash,
        username=username,
        status=status,
    )
    db.add(user)
    await db.flush()

    if role_ids:
        result = await db.execute(select(Role).where(Role.id.in_(role_ids)))
        roles = list(result.scalars().all())
        user.roles = roles

    # Create default settings
    settings_obj = UserSettings(user_id=user.id)
    db.add(settings_obj)
    await db.flush()

    await db.refresh(user, ["roles", "settings"])
    return user


async def update_user(
    db: AsyncSession,
    user: User,
    name: str | None = None,
    email: str | None = None,
    password_hash: str | None = None,
    username: str | None = None,
    status: str | None = None,
    role_ids: list[uuid.UUID] | None = None,
) -> User:
    if name is not None:
        user.name = name
    if email is not None:
        user.email = email
    if password_hash is not None:
        user.password_hash = password_hash
    if username is not None:
        user.username = username
    if status is not None:
        user.status = status

    if role_ids is not None:
        result = await db.execute(select(Role).where(Role.id.in_(role_ids)))
        roles = list(result.scalars().all())
        user.roles = roles

    await db.flush()
    await db.refresh(user, ["roles", "settings"])
    return user


async def delete_user(db: AsyncSession, user: User) -> None:
    await db.delete(user)
    await db.flush()


async def get_or_create_settings(db: AsyncSession, user: User) -> UserSettings:
    if user.settings:
        return user.settings
    settings_obj = UserSettings(user_id=user.id)
    db.add(settings_obj)
    await db.flush()
    await db.refresh(user, ["settings"])
    return settings_obj


async def update_user_avatar(db: AsyncSession, user: User, avatar_path: str) -> User:
    settings_obj = await get_or_create_settings(db, user)
    settings_obj.avatar = avatar_path
    await db.flush()
    return user
