import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.telefono import EstadoTelefono, Telefono, Tipologia


def _with_relations(query):
    return query.options(
        selectinload(Telefono.estado),
        selectinload(Telefono.tipologia),
        selectinload(Telefono.trabajador),
    )


async def list_telefonos(
    db: AsyncSession,
    page: int = 1,
    per_page: int = 20,
    search: str | None = None,
    activo: bool | None = None,
    estado_id: uuid.UUID | None = None,
    trabajador_id: uuid.UUID | None = None,
) -> tuple[list[Telefono], int]:
    query = select(Telefono)

    if search:
        query = query.where(
            or_(
                Telefono.numero.ilike(f"%{search}%"),
                Telefono.imei.ilike(f"%{search}%"),
                Telefono.marca.ilike(f"%{search}%"),
                Telefono.modelo.ilike(f"%{search}%"),
            )
        )

    if activo is not None:
        query = query.where(Telefono.activo == activo)

    if estado_id:
        query = query.where(Telefono.estado_id == estado_id)

    if trabajador_id:
        query = query.where(Telefono.trabajador_id == trabajador_id)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = _with_relations(query).order_by(Telefono.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    items = list(result.scalars().all())

    return items, total


async def get_telefono_by_id(db: AsyncSession, telefono_id: uuid.UUID) -> Telefono | None:
    result = await db.execute(_with_relations(select(Telefono)).where(Telefono.id == telefono_id))
    return result.scalar_one_or_none()


async def create_telefono(db: AsyncSession, data: dict) -> Telefono:
    t = Telefono(**data)
    db.add(t)
    await db.flush()
    result = await db.execute(_with_relations(select(Telefono)).where(Telefono.id == t.id))
    return result.scalar_one()


async def update_telefono(db: AsyncSession, t: Telefono, data: dict) -> Telefono:
    for key, value in data.items():
        setattr(t, key, value)
    await db.flush()
    result = await db.execute(_with_relations(select(Telefono)).where(Telefono.id == t.id))
    return result.scalar_one()


async def delete_telefono(db: AsyncSession, t: Telefono) -> None:
    await db.delete(t)
    await db.flush()


async def list_estados(db: AsyncSession) -> list[EstadoTelefono]:
    result = await db.execute(select(EstadoTelefono).order_by(EstadoTelefono.nombre))
    return list(result.scalars().all())


async def list_tipologias(db: AsyncSession) -> list[Tipologia]:
    result = await db.execute(select(Tipologia).order_by(Tipologia.nombre))
    return list(result.scalars().all())
