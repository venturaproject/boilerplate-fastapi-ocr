from __future__ import annotations

import io

from PIL import Image
from sqlalchemy import text

from app.database import AsyncSessionLocal

SYNC = "/api/ext/ocr"
USAGE = "/api/ext/ocr/usage"


def _png(size: tuple[int, int] = (64, 32)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, "white").save(buf, format="PNG")
    return buf.getvalue()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _set_client(name: str, **fields: object) -> None:
    sets = ", ".join(f"{k} = :{k}" for k in fields)
    async with AsyncSessionLocal() as s, s.begin():
        await s.execute(
            text(f"UPDATE api_clients SET {sets} WHERE name = :name"),
            {"name": name, **fields},
        )


async def test_sync_response_carries_ratelimit_headers(client, ocr_token):
    r = await client.post(SYNC, files={"file": ("d.png", _png(), "image/png")}, headers=_auth(ocr_token))
    assert r.status_code == 200, r.text
    assert "X-RateLimit-Limit" in r.headers
    assert "X-RateLimit-Remaining" in r.headers
    assert "X-RateLimit-Reset" in r.headers
    assert int(r.headers["X-RateLimit-Remaining"]) < int(r.headers["X-RateLimit-Limit"])


async def test_per_client_rate_limit_override_returns_429(client, ocr_token):
    await _set_client("test-ocr", rate_limit="2/60")
    statuses = []
    for _ in range(4):
        r = await client.post(SYNC, files={"file": ("d.png", _png(), "image/png")}, headers=_auth(ocr_token))
        statuses.append(r.status_code)
    assert statuses[:2] == [200, 200]
    assert statuses[2] == 429
    assert (
        "Retry-After"
        in (await client.post(SYNC, files={"file": ("d.png", _png(), "image/png")}, headers=_auth(ocr_token))).headers
    )


async def test_monthly_page_quota_blocks_further_writes(client, ocr_token):
    await _set_client("test-ocr", monthly_page_quota=1)

    r1 = await client.post(SYNC, files={"file": ("d.png", _png(), "image/png")}, headers=_auth(ocr_token))
    assert r1.status_code == 200, r1.text

    r2 = await client.post(SYNC, files={"file": ("d.png", _png(), "image/png")}, headers=_auth(ocr_token))
    assert r2.status_code == 429
    assert r2.headers["X-Quota-Limit"] == "1"
    assert r2.headers["X-Quota-Remaining"] == "0"
    assert "cuota" in r2.json()["detail"].lower()


async def test_usage_endpoint_reports_pages_and_quota(client, ocr_token):
    await _set_client("test-ocr", monthly_page_quota=10)
    await client.post(SYNC, files={"file": ("d.png", _png(), "image/png")}, headers=_auth(ocr_token))

    r = await client.get(USAGE, headers=_auth(ocr_token))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["pages"] == 1
    assert body["requests"] >= 1
    assert body["monthly_page_quota"] == 10
    assert body["quota_remaining"] == 9
    assert "/" in body["rate_limit"]


async def test_read_scope_is_not_quota_limited(client, ocr_token):
    await _set_client("test-ocr", monthly_page_quota=1)
    # exhaust the quota
    await client.post(SYNC, files={"file": ("d.png", _png(), "image/png")}, headers=_auth(ocr_token))
    # a read endpoint must still work
    r = await client.get(USAGE, headers=_auth(ocr_token))
    assert r.status_code == 200
