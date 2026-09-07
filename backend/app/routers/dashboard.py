from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.dependencies import require_permission
from app.models.dispositivo import Dispositivo
from app.models.telefono import Telefono
from app.models.trabajador import Trabajador
from app.schemas.dashboard import (
    DashboardResponse,
    MonthlyWorkerStat,
    PhoneStats,
    RecentDevice,
    WorkerStats,
)

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("", dependencies=[require_permission("dashboard.view")])
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    now = datetime.now(tz=UTC)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).date()

    # Worker stats
    activos_result = await db.execute(select(func.count()).select_from(Trabajador).where(Trabajador.estado == "activo"))
    activos = activos_result.scalar_one()

    con_telefono_result = await db.execute(
        select(func.count(Trabajador.id.distinct()))
        .select_from(Trabajador)
        .join(Telefono, Telefono.trabajador_id == Trabajador.id)
        .where(Telefono.activo == True)  # noqa: E712
    )
    con_telefono = con_telefono_result.scalar_one()

    incorporados_mes_result = await db.execute(
        select(func.count())
        .select_from(Trabajador)
        .where(Trabajador.fecha_incorporacion >= start_of_month)
    )
    incorporados_este_mes = incorporados_mes_result.scalar_one()

    con_imei_result = await db.execute(
        select(func.count(Trabajador.id.distinct()))
        .select_from(Trabajador)
        .join(Telefono, Telefono.trabajador_id == Trabajador.id)
        .where(Telefono.imei.isnot(None))
    )
    con_imei = con_imei_result.scalar_one()

    # Phone stats
    total_phones_result = await db.execute(
        select(func.count()).select_from(Telefono).where(Telefono.activo == True)  # noqa: E712
    )
    total_phones = total_phones_result.scalar_one()

    active_phones_result = await db.execute(
        select(func.count())
        .select_from(Telefono)
        .where(Telefono.activo == True, Telefono.trabajador_id.isnot(None))  # noqa: E712
    )
    active_phones = active_phones_result.scalar_one()

    bajas_result = await db.execute(
        select(func.count()).select_from(Telefono).where(Telefono.activo == False)  # noqa: E712
    )
    bajas_phones = bajas_result.scalar_one()

    sin_datos_result = await db.execute(
        select(func.count())
        .select_from(Telefono)
        .where(Telefono.activo == True, Telefono.imei.is_(None))  # noqa: E712
    )
    sin_datos = sin_datos_result.scalar_one()

    # Recent devices
    limit = settings.dashboard_recent_devices_limit
    recent_result = await db.execute(
        select(Dispositivo)
        .options(
            selectinload(Dispositivo.marca),
            selectinload(Dispositivo.modelo),
            selectinload(Dispositivo.trabajador),
        )
        .order_by(Dispositivo.updated_at.desc())
        .limit(limit)
    )
    recent_devices_rows = list(recent_result.scalars().all())
    recent_devices = [
        RecentDevice(
            id=str(d.id),
            numero=d.numero,
            grupo=d.grupo,
            updated_at=d.updated_at.isoformat(),
            marca=d.marca.nombre if d.marca else None,
            modelo=d.modelo.nombre if d.modelo else None,
            employee_nombre=d.trabajador.nombre if d.trabajador else None,
        )
        for d in recent_devices_rows
    ]

    # Monthly worker stats (last 12 months)
    twelve_months_ago = (now - timedelta(days=365)).date()
    monthly_result = await db.execute(
        select(
            extract("year", Trabajador.fecha_incorporacion).label("year"),
            extract("month", Trabajador.fecha_incorporacion).label("month"),
            func.count(Trabajador.id).label("total"),
        )
        .where(Trabajador.fecha_incorporacion >= twelve_months_ago)
        .group_by("year", "month")
        .order_by("year", "month")
    )
    monthly_stats = [
        MonthlyWorkerStat(
            month=f"{int(row.year):04d}-{int(row.month):02d}",
            incorporations=int(row.total),
        )
        for row in monthly_result
    ]

    return DashboardResponse(
        stats=WorkerStats(
            activos=activos,
            conTelefono=con_telefono,
            incorporadosEsteMes=incorporados_este_mes,
            conImei=con_imei,
        ),
        phoneStats=PhoneStats(
            total=total_phones,
            activos=active_phones,
            congelados=0,
            bajas=bajas_phones,
            sinDatos=sin_datos,
        ),
        recentDevices=recent_devices,
        monthlyWorkerStats=monthly_stats,
    )
