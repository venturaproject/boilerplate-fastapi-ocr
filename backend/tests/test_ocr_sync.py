from __future__ import annotations

import io

from PIL import Image

SYNC = "/api/ext/ocr"


def _png(size: tuple[int, int] = (64, 32)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, "white").save(buf, format="PNG")
    return buf.getvalue()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_sync_ocr_returns_result(client, ocr_token):
    files = {"file": ("doc.png", _png(), "image/png")}
    r = await client.post(SYNC, files=files, headers=_auth(ocr_token))

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["engine"] == "fake"
    assert body["lang"] == "es"
    assert body["page_count"] == 1
    assert body["pages"][0]["lines"][0]["text"].startswith("[fake-ocr")
    assert body["pages"][0]["lines"][0]["box"]
    assert body["text"]


async def test_sync_ocr_honours_lang_form_field(client, ocr_token):
    files = {"file": ("doc.png", _png(), "image/png")}
    r = await client.post(SYNC, files=files, data={"lang": "en"}, headers=_auth(ocr_token))
    assert r.status_code == 200
    assert r.json()["lang"] == "en"


async def test_sync_ocr_requires_token(client):
    r = await client.post(SYNC, files={"file": ("d.png", _png(), "image/png")})
    assert r.status_code == 401


async def test_sync_ocr_requires_write_scope(client, ocr_token_readonly):
    r = await client.post(
        SYNC,
        files={"file": ("d.png", _png(), "image/png")},
        headers=_auth(ocr_token_readonly),
    )
    assert r.status_code == 403


async def test_sync_ocr_rejects_unsupported_type(client, ocr_token):
    files = {"file": ("notes.txt", b"hello world", "text/plain")}
    r = await client.post(SYNC, files=files, headers=_auth(ocr_token))
    assert r.status_code == 415


async def test_sync_ocr_rejects_oversized(client, ocr_token, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "ocr_sync_max_bytes", 10)
    files = {"file": ("big.png", _png((128, 128)), "image/png")}
    r = await client.post(SYNC, files=files, headers=_auth(ocr_token))
    assert r.status_code == 413
