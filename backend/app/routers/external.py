from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import ExtClientContext, require_scope
from app.ratelimit import rate_limit
from app.repositories import dispositivo as dispositivo_repo
from app.repositories import telefono as telefono_repo
from app.repositories import trabajador as trabajador_repo
from app.schemas.dispositivo import DispositivoOut
from app.schemas.telefono import TelefonoOut
from app.schemas.trabajador import TrabajadorOut

router = APIRouter(prefix="/api/ext", tags=["external"])

_api_limit, _api_per = settings.throttle(settings.throttle_ext_api)
_ext_api_rl = Depends(rate_limit("ext_api", _api_limit, _api_per))


@router.get("/trabajadores", dependencies=[_ext_api_rl])
async def ext_list_trabajadores(
    ctx: ExtClientContext = require_scope("trabajadores:read"),
    db: AsyncSession = Depends(get_db),
):
    items, total = await trabajador_repo.list_trabajadores(db, per_page=10000)
    return {
        "data": [
            TrabajadorOut(
                id=t.id,
                nombre=t.nombre,
                apellido=t.apellido,
                nombre_completo=t.nombre_completo,
                synergy_res_id=t.synergy_res_id,
                dni=t.dni,
                email=t.email,
                telefono=t.telefono,
                estado=t.estado,
                emp_stat=t.emp_stat,
                cargo=t.cargo,
                departamento=t.departamento,
                loc=t.loc,
                ubicacion=t.ubicacion,
                ciudad=t.ciudad,
                fecha_incorporacion=t.fecha_incorporacion,
                fecha_baja=t.fecha_baja,
                observaciones=t.observaciones,
                created_at=t.created_at,
                updated_at=t.updated_at,
            )
            for t in items
        ],
        "total": total,
    }


@router.get("/telefonos", dependencies=[_ext_api_rl])
async def ext_list_telefonos(
    ctx: ExtClientContext = require_scope("telefonos:read"),
    db: AsyncSession = Depends(get_db),
):
    items, total = await telefono_repo.list_telefonos(db, per_page=10000)
    return {
        "data": [TelefonoOut.model_validate(t) for t in items],
        "total": total,
    }


@router.get("/dispositivos", dependencies=[_ext_api_rl])
async def ext_list_dispositivos(
    ctx: ExtClientContext = require_scope("dispositivos:read"),
    db: AsyncSession = Depends(get_db),
):
    items, total = await dispositivo_repo.list_dispositivos(db, per_page=10000)
    return {
        "data": [DispositivoOut.model_validate(d) for d in items],
        "total": total,
    }
