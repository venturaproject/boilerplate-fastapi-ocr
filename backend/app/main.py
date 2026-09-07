import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import anyio.to_thread
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import domain as _domain  # noqa: F401  -- registra handlers/subscribers/traductores en los buses
from app.config import settings
from app.exceptions import AppException
from app.idempotency import IdempotencyMiddleware
from app.middleware.csrf import CSRFMiddleware
from app.middleware.private_media import PrivateMediaMiddleware
from app.routers import (
    api_clients,
    auth,
    csrf,
    dashboard,
    dispositivos,
    documents,
    ext_ocr,
    external,
    external_auth,
    notifications,
    ocr,
    permissions,
    roles,
    telefonos,
    trabajadores,
    users,
    webhooks,
)
from app.routers import (
    settings as settings_router,
)
from app.services.ocr.engine import warmup as ocr_warmup

logger = logging.getLogger("app.main")
_bg_tasks: set[asyncio.Task] = set()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    if settings.ocr_warmup_on_startup and settings.ocr_engine != "fake":
        async def _warm() -> None:
            try:
                await anyio.to_thread.run_sync(ocr_warmup, settings.ocr_warmup_langs_list)
            except Exception:
                logger.exception("OCR warmup falló")

        task = asyncio.create_task(_warm())
        _bg_tasks.add(task)
        task.add_done_callback(_bg_tasks.discard)
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    redirect_slashes=False,
    lifespan=lifespan,
)

# ── Middleware stack (order matters) ──────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "X-CSRF-Token", "X-CSRFToken"],
)

app.add_middleware(PrivateMediaMiddleware)
app.add_middleware(CSRFMiddleware)
app.add_middleware(IdempotencyMiddleware)

# ── Exception handlers ────────────────────────────────────────────────────────

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(csrf.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(roles.router)
app.include_router(permissions.router)
app.include_router(trabajadores.router)
app.include_router(telefonos.router)
app.include_router(dispositivos.router)
app.include_router(documents.router)
app.include_router(dashboard.router)
app.include_router(api_clients.router)
app.include_router(notifications.router)
app.include_router(settings_router.router)
app.include_router(external_auth.router)
app.include_router(external.router)
app.include_router(webhooks.router)
app.include_router(ocr.router)
app.include_router(ext_ocr.router)


@app.get("/api/health")
async def health():
    from app.services.ocr.engine import is_ready, warmed_langs

    return {
        "status": "ok",
        "app": settings.app_name,
        "ocr": {
            "engine": settings.ocr_engine,
            "ready": is_ready(),
            "warmed_langs": warmed_langs(),
        },
    }
