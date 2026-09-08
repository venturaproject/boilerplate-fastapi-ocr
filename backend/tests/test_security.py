from __future__ import annotations

from sqlalchemy import text

from app.config import settings
from app.database import AsyncSessionLocal

LOGIN = "/api/v1/auth/login"


async def _bad_login(client, login: str = "admin@example.com"):
    return await client.post(LOGIN, json={"login": login, "password": "wrong"})


async def test_account_locks_after_max_attempts(client, monkeypatch):
    monkeypatch.setattr(settings, "login_max_attempts", 3)
    monkeypatch.setattr(settings, "login_lockout_minutes", 15)
    # avoid the IP rate-limiter masking the lockout
    monkeypatch.setattr(settings, "throttle_login", "50/60")

    for _ in range(3):
        assert (await _bad_login(client)).status_code == 401

    # now locked — even the correct password is refused with 403
    r = await client.post(LOGIN, json={"login": settings.admin_email, "password": settings.admin_password})
    assert r.status_code == 403
    assert "bloqueada" in r.json()["detail"].lower()


async def test_successful_login_clears_the_counter(client, monkeypatch):
    monkeypatch.setattr(settings, "login_max_attempts", 5)
    monkeypatch.setattr(settings, "throttle_login", "50/60")

    await _bad_login(client)
    await _bad_login(client)
    ok = await client.post(LOGIN, json={"login": settings.admin_email, "password": settings.admin_password})
    assert ok.status_code == 200

    async with AsyncSessionLocal() as s:
        attempts = (
            await s.execute(
                text("SELECT failed_login_attempts FROM users WHERE email = :e"), {"e": settings.admin_email}
            )
        ).scalar_one()
    assert attempts == 0


async def test_login_writes_audit_events(client, monkeypatch):
    monkeypatch.setattr(settings, "throttle_login", "50/60")
    await _bad_login(client, "ghost@example.com")
    await client.post(LOGIN, json={"login": settings.admin_email, "password": settings.admin_password})

    async with AsyncSessionLocal() as s:
        rows = (await s.execute(text("SELECT action, actor_label FROM audit_events ORDER BY created_at"))).all()
    actions = {a for a, _ in rows}
    assert "auth.login.failed" in actions
    assert "auth.login.ok" in actions


async def test_audit_endpoint_requires_auth(client):
    assert (await client.get("/api/v1/audit")).status_code in (401, 403)


async def test_audit_endpoint_ok_for_admin(admin_client):
    r = await admin_client.get("/api/v1/audit")
    assert r.status_code == 200
    assert "data" in r.json()


async def test_api_client_lifecycle_is_audited(admin_client):
    created = await admin_client.post("/api/v1/api-clients", json={"name": "audited", "scopes": ["ocr:read"]})
    cid = created.json()["client"]["id"]
    await admin_client.post(f"/api/v1/api-clients/{cid}/rotate")
    await admin_client.delete(f"/api/v1/api-clients/{cid}")

    events = (await admin_client.get("/api/v1/audit?per_page=200")).json()["data"]
    actions = [e["action"] for e in events]
    assert "api_client.created" in actions
    assert "api_client.rotated" in actions
    assert "api_client.revoked" in actions
