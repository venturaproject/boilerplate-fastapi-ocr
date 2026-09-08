from __future__ import annotations

import io

from PIL import Image

from app.ocr.processor import _deliver_due_callbacks, drain_once

JOBS = "/api/ext/ocr/jobs"


def _png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (48, 24), "white").save(buf, format="PNG")
    return buf.getvalue()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class _FailingClient:
    def __init__(self, *a, **k) -> None:
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a) -> bool:
        return False

    class _Resp:
        status_code = 500
        is_success = False

    async def post(self, *a, **k):
        return self._Resp()


async def _submit(client, token) -> str:
    r = await client.post(
        JOBS,
        files={"file": ("d.png", _png(), "image/png")},
        data={"callback_url": "https://example.test/hook"},
        headers=_auth(token),
    )
    assert r.status_code == 202
    return r.json()["id"]


async def test_failed_callback_is_retried_then_dead_lettered(client, ocr_token, monkeypatch):
    import app.services.ocr.callback as cb
    from app.config import settings

    monkeypatch.setattr(cb.httpx, "AsyncClient", _FailingClient)
    monkeypatch.setattr(settings, "ocr_callback_max_attempts", 3)
    monkeypatch.setattr(settings, "ocr_callback_backoff_base_seconds", 0)  # retry immediately

    job_id = await _submit(client, ocr_token)
    await drain_once()  # runs OCR + first callback attempt (fails)

    r = await client.get(f"{JOBS}/{job_id}", headers=_auth(ocr_token))
    body = r.json()
    assert body["callback_status"] == "http_500"
    assert body["callback_attempts"] == 1
    assert body["next_callback_at"] is not None

    # backoff base 0 -> due immediately; two more retries hit the cap
    assert await _deliver_due_callbacks() == 1
    assert await _deliver_due_callbacks() == 1

    body = (await client.get(f"{JOBS}/{job_id}", headers=_auth(ocr_token))).json()
    assert body["callback_attempts"] == 3
    assert body["next_callback_at"] is None  # dead-lettered


async def test_redeliver_resets_the_callback(client, ocr_token, monkeypatch):
    import app.services.ocr.callback as cb
    from app.config import settings

    monkeypatch.setattr(cb.httpx, "AsyncClient", _FailingClient)
    monkeypatch.setattr(settings, "ocr_callback_max_attempts", 1)

    job_id = await _submit(client, ocr_token)
    await drain_once()
    assert (await client.get(f"{JOBS}/{job_id}", headers=_auth(ocr_token))).json()["next_callback_at"] is None

    r = await client.post(f"{JOBS}/{job_id}/redeliver", headers=_auth(ocr_token))
    assert r.status_code == 200
    body = (await client.get(f"{JOBS}/{job_id}", headers=_auth(ocr_token))).json()
    assert body["callback_attempts"] == 0
    assert body["next_callback_at"] is not None


async def test_callback_failed_filter(client, ocr_token, monkeypatch):
    import app.services.ocr.callback as cb
    from app.config import settings

    monkeypatch.setattr(cb.httpx, "AsyncClient", _FailingClient)
    monkeypatch.setattr(settings, "ocr_callback_max_attempts", 1)

    await _submit(client, ocr_token)
    await drain_once()

    r = await client.get(f"{JOBS}?callback=failed", headers=_auth(ocr_token))
    assert r.json()["total"] == 1


async def test_redeliver_without_callback_url_is_422(client, ocr_token):
    r = await client.post(JOBS, files={"file": ("d.png", _png(), "image/png")}, headers=_auth(ocr_token))
    job_id = r.json()["id"]
    r = await client.post(f"{JOBS}/{job_id}/redeliver", headers=_auth(ocr_token))
    assert r.status_code == 422
