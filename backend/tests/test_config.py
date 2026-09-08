from __future__ import annotations

from app.config import settings


async def test_public_config_is_open_and_returns_app_name(client):
    r = await client.get("/api/v1/config")
    assert r.status_code == 200
    assert r.json() == {"app_name": settings.app_name}


async def test_openapi_title_derives_from_app_name(client):
    spec = (await client.get("/api/openapi.json")).json()
    assert spec["info"]["title"] == f"{settings.app_name} API"
    assert spec["paths"]["/api/v1/config"]["get"]["security"] == []
