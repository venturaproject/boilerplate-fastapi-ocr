from __future__ import annotations

import importlib

from httpx import ASGITransport, AsyncClient


async def test_openapi_served_and_branded(client):
    r = await client.get("/api/openapi.json")
    assert r.status_code == 200
    spec = r.json()
    assert spec["openapi"].startswith("3.")
    assert spec["info"]["title"] == "Ocrer API"
    assert spec["info"]["description"]
    assert spec["servers"]


async def test_openapi_declares_both_auth_schemes(client):
    spec = (await client.get("/api/openapi.json")).json()
    schemes = spec["components"]["securitySchemes"]
    assert schemes["ExternalBearer"]["type"] == "http"
    assert schemes["ExternalBearer"]["scheme"] == "bearer"
    assert schemes["SessionCookie"]["in"] == "cookie"


async def test_openapi_security_applied_by_surface(client):
    spec = (await client.get("/api/openapi.json")).json()
    paths = spec["paths"]

    assert paths["/api/ext/ocr"]["post"]["security"] == [{"ExternalBearer": []}]
    assert paths["/api/v1/users"]["get"]["security"] == [{"SessionCookie": []}]
    # public
    assert paths["/api/v1/auth/login"]["post"]["security"] == []
    assert paths["/api/ext/auth/token"]["post"]["security"] == []
    assert paths["/api/health"]["get"]["security"] == []


async def test_docs_ui_available(client):
    assert (await client.get("/api/docs")).status_code == 200
    assert (await client.get("/api/redoc")).status_code == 200


async def test_docs_disabled_hides_everything(monkeypatch):
    """DOCS_ENABLED=false → Swagger UI, ReDoc and the spec all 404."""
    from app import config as config_mod
    from app import main as main_mod

    monkeypatch.setattr(config_mod.settings, "docs_enabled", False)
    importlib.reload(main_mod)
    try:
        transport = ASGITransport(app=main_mod.app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            assert (await c.get("/api/docs")).status_code == 404
            assert (await c.get("/api/redoc")).status_code == 404
            assert (await c.get("/api/openapi.json")).status_code == 404
            # the API itself still works
            assert (await c.get("/api/health")).status_code == 200
    finally:
        monkeypatch.undo()
        importlib.reload(main_mod)
