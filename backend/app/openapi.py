"""Custom OpenAPI schema: brand metadata, tag docs and the two auth schemes.

FastAPI already derives the spec from the routes; this layer adds what it can't
infer — security schemes (the app parses the cookie / bearer by hand), a real
description, ordered tags and a relative `servers` entry.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

API_VERSION = "1.0.0"

DESCRIPTION = """\
API de OCR (PaddleOCR) con dos superficies:

* **API externa** (`/api/ext/*`) — para sistemas de terceros. Flujo
  `client_credentials`: `POST /api/ext/auth/token` con `client_id` / `client_secret`
  devuelve un **Bearer** con *scopes* (`ocr:read`, `ocr:write`). Rate-limit y cuota
  mensual de páginas por cliente; cabeceras `X-RateLimit-*` / `X-Quota-*` en cada
  respuesta.
* **Panel** (`/api/v1/*`) — para el frontend de administración. Autenticación por
  **cookie JWT** (`POST /api/v1/auth/login`) + CSRF en métodos mutantes.

Toda llamada OCR queda registrada en `documents`. Los trabajos asíncronos
(`/api/ext/ocr/jobs`) admiten `callback_url` firmado (HMAC-SHA256) con reintentos
y *dead-letter*.
"""

TAGS: list[dict[str, str]] = [
    {"name": "external-auth", "description": "Emisión y refresco de tokens Bearer (client_credentials)."},
    {"name": "external-ocr", "description": "OCR para clientes externos: síncrono, clasificación, jobs, lotes, uso."},
    {"name": "auth", "description": "Login del panel (cookie JWT), perfil y avatar."},
    {"name": "ocr", "description": "OCR desde el panel (misma lógica que la API externa, auth por cookie)."},
    {"name": "documents", "description": "Registro de todo lo procesado por la API."},
    {"name": "audit", "description": "Log de eventos de seguridad (logins, cambios RBAC, clientes API)."},
    {"name": "api-clients", "description": "Alta/baja de clientes externos, scopes, cuotas y rotación de secreto."},
    {"name": "users", "description": "Gestión de usuarios."},
    {"name": "roles", "description": "Roles y sus permisos."},
    {"name": "permissions", "description": "Catálogo de permisos."},
    {"name": "dashboard", "description": "Métricas agregadas para el panel."},
    {"name": "settings", "description": "Preferencias del usuario autenticado."},
    {"name": "notifications", "description": "Notificaciones del panel."},
    {"name": "csrf", "description": "Emisión del token CSRF."},
    {"name": "config", "description": "Configuración pública que la SPA lee al arrancar."},
    {"name": "metrics", "description": "Métricas Prometheus (`GET /metrics`)."},
]

_SECURITY_SCHEMES: dict[str, Any] = {
    "ExternalBearer": {
        "type": "http",
        "scheme": "bearer",
        "description": "Token del flujo client_credentials — `POST /api/ext/auth/token`.",
    },
    "SessionCookie": {
        "type": "apiKey",
        "in": "cookie",
        "name": "access_token",
        "description": "Cookie JWT del panel — se fija con `POST /api/v1/auth/login`.",
    },
}

# Rutas accesibles sin autenticación.
_PUBLIC_PATHS = {
    "/api/health",
    "/metrics",
    "/api/v1/config",
    "/api/v1/csrf/",
    "/api/v1/auth/login",
    "/api/v1/auth/logout",
    "/api/v1/auth/refresh",
    "/api/ext/auth/token",
    "/api/ext/auth/refresh",
}


def _security_for(path: str) -> list[dict[str, list[str]]] | None:
    if path in _PUBLIC_PATHS:
        return []
    if path.startswith("/api/ext/"):
        return [{"ExternalBearer": []}]
    if path.startswith("/api/v1/"):
        return [{"SessionCookie": []}]
    return None


def custom_openapi(app: FastAPI) -> dict[str, Any]:
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=API_VERSION,
        description=DESCRIPTION,
        routes=app.routes,
        tags=TAGS,
        servers=[{"url": "/", "description": "Este servidor"}],
        contact={"name": "Equipo Ocrer"},
        license_info={"name": "MIT"},
    )

    schema.setdefault("components", {})["securitySchemes"] = _SECURITY_SCHEMES
    for path, item in schema.get("paths", {}).items():
        security = _security_for(path)
        if security is None:
            continue
        for method in ("get", "post", "put", "patch", "delete"):
            if method in item:
                item[method]["security"] = security

    app.openapi_schema = schema
    return schema
