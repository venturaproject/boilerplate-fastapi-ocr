from __future__ import annotations

from sqlalchemy import func, select

from app.database import AsyncSessionLocal
from app.idempotency.models import IdempotencyKey

LOGIN = "/api/v1/auth/login"


async def _keys() -> int:
    async with AsyncSessionLocal() as s:
        return (await s.execute(select(func.count()).select_from(IdempotencyKey))).scalar_one()


async def test_same_key_and_body_replays(client):
    body = {"login": "nope@e.com", "password": "bad"}
    h = {"Idempotency-Key": "k1"}
    r1 = await client.post(LOGIN, json=body, headers=h)
    r2 = await client.post(LOGIN, json=body, headers=h)

    assert r1.status_code == 401
    assert r2.status_code == 401
    assert r2.headers.get("idempotent-replay") == "true"
    assert await _keys() == 1


async def test_same_key_different_body_is_422(client):
    h = {"Idempotency-Key": "k2"}
    await client.post(LOGIN, json={"login": "a@e.com", "password": "bad"}, headers=h)
    r2 = await client.post(LOGIN, json={"login": "b@e.com", "password": "bad"}, headers=h)
    assert r2.status_code == 422


async def test_no_key_header_no_dedup(client):
    for _ in range(2):
        await client.post(LOGIN, json={"login": "c@e.com", "password": "bad"})
    assert await _keys() == 0
