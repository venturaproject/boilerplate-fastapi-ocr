from __future__ import annotations

import io

from PIL import Image

from app.ocr.processor import drain_once

JOBS = "/api/ext/ocr/jobs"


def _png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (48, 24), "white").save(buf, format="PNG")
    return buf.getvalue()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_job_lifecycle(client, ocr_token):
    r = await client.post(
        JOBS, files={"file": ("d.png", _png(), "image/png")}, headers=_auth(ocr_token)
    )
    assert r.status_code == 202, r.text
    created = r.json()
    assert created["status"] == "pending"
    job_id = created["id"]

    assert await drain_once() == 1

    r = await client.get(f"{JOBS}/{job_id}", headers=_auth(ocr_token))
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "done"
    assert body["page_count"] == 1
    assert body["result"]["page_count"] == 1
    assert body["result"]["text"]


async def test_job_listing_only_shows_own_client(client, ocr_token, ocr_token_readonly):
    r = await client.post(
        JOBS, files={"file": ("d.png", _png(), "image/png")}, headers=_auth(ocr_token)
    )
    job_id = r.json()["id"]

    r = await client.get(f"{JOBS}/{job_id}", headers=_auth(ocr_token_readonly))
    assert r.status_code == 404

    r = await client.get(JOBS, headers=_auth(ocr_token_readonly))
    assert r.status_code == 200
    assert r.json()["total"] == 0


async def test_job_fires_callback(client, ocr_token, monkeypatch):
    import app.ocr.processor as processor

    received: dict = {}

    class _FakeResp:
        status_code = 200
        is_success = True

    class _FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self) -> _FakeClient:
            return self

        async def __aexit__(self, *args) -> bool:
            return False

        async def post(self, url: str, json: dict) -> _FakeResp:
            received["url"] = url
            received["json"] = json
            return _FakeResp()

    monkeypatch.setattr(processor.httpx, "AsyncClient", _FakeClient)

    r = await client.post(
        JOBS,
        files={"file": ("d.png", _png(), "image/png")},
        data={"callback_url": "https://example.test/hook"},
        headers=_auth(ocr_token),
    )
    assert r.status_code == 202

    await drain_once()

    assert received["url"] == "https://example.test/hook"
    assert received["json"]["status"] == "done"
    assert received["json"]["result"]["page_count"] == 1

    r = await client.get(f"{JOBS}/{r.json()['id']}", headers=_auth(ocr_token))
    assert r.json()["callback_status"] == "http_200"


async def test_job_rejects_bad_callback_url(client, ocr_token):
    r = await client.post(
        JOBS,
        files={"file": ("d.png", _png(), "image/png")},
        data={"callback_url": "ftp://nope"},
        headers=_auth(ocr_token),
    )
    assert r.status_code == 422
