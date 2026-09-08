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


async def test_sync_ocr_rejects_unknown_lang(client, ocr_token):
    r = await client.post(
        SYNC,
        files={"file": ("d.png", _png(), "image/png")},
        data={"lang": "klingon"},
        headers=_auth(ocr_token),
    )
    assert r.status_code == 422


async def test_sync_ocr_caches_by_content_hash(client, ocr_token):
    png = _png()
    r1 = await client.post(SYNC, files={"file": ("a.png", png, "image/png")}, headers=_auth(ocr_token))
    r2 = await client.post(SYNC, files={"file": ("b.png", png, "image/png")}, headers=_auth(ocr_token))
    assert r1.status_code == r2.status_code == 200
    assert r1.json()["cached"] is False
    assert r2.json()["cached"] is True
    assert r1.json()["text"] == r2.json()["text"]

    # different lang -> not a cache hit
    r3 = await client.post(
        SYNC, files={"file": ("c.png", png, "image/png")}, data={"lang": "en"}, headers=_auth(ocr_token)
    )
    assert r3.json()["cached"] is False


async def test_sync_ocr_engine_failure_is_502(client, ocr_token, monkeypatch):
    from app.services.ocr.engine import FakeOcrEngine

    def _boom(self, pages, lang):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(FakeOcrEngine, "recognize_pages", _boom)
    r = await client.post(SYNC, files={"file": ("d.png", _png(), "image/png")}, headers=_auth(ocr_token))
    assert r.status_code == 502


async def test_sync_ocr_rejects_pixel_bomb(client, ocr_token, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "ocr_max_image_megapixels", 0.001)  # ~1000 px
    r = await client.post(SYNC, files={"file": ("big.png", _png((256, 256)), "image/png")}, headers=_auth(ocr_token))
    assert r.status_code == 413


async def test_job_long_filename_is_truncated_not_500(client, ocr_token):
    name = "x" * 600 + ".png"  # longer than the original_filename column (512)
    r = await client.post(
        "/api/ext/ocr/jobs",
        files={"file": (name, _png(), "image/png")},
        headers=_auth(ocr_token),
    )
    assert r.status_code == 202, r.text
    assert len(r.json()["original_filename"]) <= 512
