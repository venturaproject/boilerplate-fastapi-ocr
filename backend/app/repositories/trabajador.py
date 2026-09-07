import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trabajador import Trabajador


async def list_trabajadores(
    db: AsyncSession,
    page: int = 1,
    per_page: int = 20,
    search: str | None = None,
    estado: str | None = None,
    departamento: str | None = None,
) -> tuple[list[Trabajador], int]:
    query = select(Trabajador)

    if search:
        query = query.where(
            or_(
                Trabajador.nombre.ilike(f"%{search}%"),
                Trabajador.apellido.ilike(f"%{search}%"),
                Trabajador.dni.ilike(f"%{search}%"),
                Trabajador.email.ilike(f"%{search}%"),
                Trabajador.cargo.ilike(f"%{search}%"),
            )
        )

    if estado:
        query = query.where(Trabajador.estado == estado)

    if departamento:
        query = query.where(Trabajador.departamento.ilike(f"%{departamento}%"))

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(Trabajador.nombre, Trabajador.apellido).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    items = list(result.scalars().all())

    return items, total


async def get_trabajador_by_id(db: AsyncSession, trabajador_id: uuid.UUID) -> Trabajador | None:
    result = await db.execute(select(Trabajador).where(Trabajador.id == trabajador_id))
    return result.scalar_one_or_none()


async def get_by_synergy_res_id(db: AsyncSession, synergy_res_id: int) -> Trabajador | None:
    result = await db.execute(select(Trabajador).where(Trabajador.synergy_res_id == synergy_res_id))
    return result.scalar_one_or_none()


async def create_trabajador(db: AsyncSession, data: dict) -> Trabajador:
    t = Trabajador(**data)
    db.add(t)
    await db.flush()
    await db.refresh(t)
    return t


async def update_trabajador(db: AsyncSession, t: Trabajador, data: dict) -> Trabajador:
    for key, value in data.items():
        setattr(t, key, value)
    await db.flush()
    await db.refresh(t)
    return t


async def delete_trabajador(db: AsyncSession, t: Trabajador) -> None:
    await db.delete(t)
    await db.flush()
