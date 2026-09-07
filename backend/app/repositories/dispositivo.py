import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.dispositivo import Dispositivo


def _with_relations(query):
    return query.options(
        selectinload(Dispositivo.marca),
        selectinload(Dispositivo.modelo),
        selectinload(Dispositivo.trabajador),
    )


async def list_dispositivos(
    db: AsyncSession,
    page: int = 1,
    per_page: int = 20,
    search: str | None = None,
    estado: str | None = None,
    trabajador_id: uuid.UUID | None = None,
) -> tuple[list[Dispositivo], int]:
    query = select(Dispositivo)

    if search:
        query = query.where(
            or_(
                Dispositivo.numero.ilike(f"%{search}%"),
                Dispositivo.imei.ilike(f"%{search}%"),
                Dispositivo.serie.ilike(f"%{search}%"),
                Dispositivo.grupo.ilike(f"%{search}%"),
            )
        )

    if estado:
        query = query.where(Dispositivo.estado == estado)

    if trabajador_id:
        query = query.where(Dispositivo.trabajador_id == trabajador_id)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = _with_relations(query).order_by(Dispositivo.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    items = list(result.scalars().all())

    return items, total


async def get_dispositivo_by_id(db: AsyncSession, dispositivo_id: uuid.UUID) -> Dispositivo | None:
    result = await db.execute(_with_relations(select(Dispositivo)).where(Dispositivo.id == dispositivo_id))
    return result.scalar_one_or_none()


async def create_dispositivo(db: AsyncSession, data: dict) -> Dispositivo:
    d = Dispositivo(**data)
    db.add(d)
    await db.flush()
    result = await db.execute(_with_relations(select(Dispositivo)).where(Dispositivo.id == d.id))
    return result.scalar_one()


async def update_dispositivo(db: AsyncSession, d: Dispositivo, data: dict) -> Dispositivo:
    for key, value in data.items():
        setattr(d, key, value)
    await db.flush()
    result = await db.execute(_with_relations(select(Dispositivo)).where(Dispositivo.id == d.id))
    return result.scalar_one()


async def delete_dispositivo(db: AsyncSession, d: Dispositivo) -> None:
    await db.delete(d)
    await db.flush()
