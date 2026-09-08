from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings

router = APIRouter(prefix="/api/v1", tags=["config"])


class PublicConfig(BaseModel):
    """Configuración pública que el frontend lee al arrancar (sin auth)."""

    app_name: str


@router.get("/config")
async def public_config() -> PublicConfig:
    return PublicConfig(app_name=settings.app_name)
