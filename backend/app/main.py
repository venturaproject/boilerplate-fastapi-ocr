import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

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
from app.observability import RequestIDMiddleware, configure_logging
from app.openapi import API_VERSION, custom_openapi
from app.routers import (
    api_clients,
    audit,
    auth,
    config,
    csrf,
    dashboard,
    documents,
    ext_ocr,
    external_auth,
    metrics,
    notifications,
    ocr,
    permissions,
    roles,
    users,
)
from app.routers import (
    settings as settings_router,
)
from app.services.ocr.engine import warmup as ocr_warmup

configure_logging(settings.log_format, settings.log_level)
logger = logging.getLogger("app.main")
_bg_tasks: set[asyncio.Task] = set()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    if settings.ocr_warmup_on_startup and settings.ocr_engine == "paddle":

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
    title=f"{settings.app_name} API",
    version=API_VERSION,
    # DOCS_ENABLED=false (producción) desactiva Swagger UI, ReDoc y openapi.json.
    docs_url="/api/docs" if settings.docs_enabled else None,
    redoc_url="/api/redoc" if settings.docs_enabled else None,
    openapi_url="/api/openapi.json" if settings.docs_enabled else None,
    redirect_slashes=False,
    lifespan=lifespan,
)

if settings.docs_enabled:

    def _openapi() -> dict[str, Any]:
        return custom_openapi(app)

    app.openapi = _openapi  # type: ignore[method-assign]

# ── Middleware stack (order matters) ──────────────────────────────────────────

# Only needed if the SPA is served from a different origin than the API. Same-origin
# deployments (nginx serves both) can leave CORS_ALLOWED_ORIGINS empty.
if settings.cors_origins_list:
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
app.add_middleware(RequestIDMiddleware)  # outermost: sets request_id + HTTP metrics

# ── Exception handlers ────────────────────────────────────────────────────────


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(csrf.router)
app.include_router(metrics.router)
app.include_router(config.router)
app.include_router(auth.router)
app.include_router(audit.router)
app.include_router(users.router)
app.include_router(roles.router)
app.include_router(permissions.router)
app.include_router(documents.router)
app.include_router(dashboard.router)
app.include_router(api_clients.router)
app.include_router(notifications.router)
app.include_router(settings_router.router)
app.include_router(external_auth.router)
app.include_router(ocr.router)
app.include_router(ext_ocr.router)


@app.get("/api/health")
async def health() -> dict[str, Any]:
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
