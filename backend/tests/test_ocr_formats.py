from __future__ import annotations

import io

from PIL import Image

SYNC = "/api/ext/ocr"


def _png(size: tuple[int, int] = (80, 40)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, "white").save(buf, format="PNG")
    return buf.getvalue()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_format_text(client, ocr_token):
    r = await client.post(
        f"{SYNC}?format=text", files={"file": ("d.png", _png(), "image/png")}, headers=_auth(ocr_token)
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/plain")
    assert "[fake-ocr" in r.text


async def test_format_hocr(client, ocr_token):
    r = await client.post(
        f"{SYNC}?format=hocr", files={"file": ("d.png", _png(), "image/png")}, headers=_auth(ocr_token)
    )
    assert r.status_code == 200
    body = r.text
    assert "class='ocr_page'" in body and "class='ocr_line'" in body
    assert "bbox 0 0 80 40" in body


async def test_format_alto(client, ocr_token):
    r = await client.post(
        f"{SYNC}?format=alto", files={"file": ("d.png", _png(), "image/png")}, headers=_auth(ocr_token)
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/xml")
    assert "<alto" in r.text and "<TextLine" in r.text and "WIDTH='80'" in r.text


async def test_format_pdf(client, ocr_token):
    r = await client.post(
        f"{SYNC}?format=pdf", files={"file": ("d.png", _png(), "image/png")}, headers=_auth(ocr_token)
    )
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:5] == b"%PDF-"


async def test_format_invalid_is_422(client, ocr_token):
    r = await client.post(
        f"{SYNC}?format=docx", files={"file": ("d.png", _png(), "image/png")}, headers=_auth(ocr_token)
    )
    assert r.status_code == 422


async def test_job_format_hocr(client, ocr_token):
    from app.ocr.processor import drain_once

    r = await client.post("/api/ext/ocr/jobs", files={"file": ("d.png", _png(), "image/png")}, headers=_auth(ocr_token))
    job_id = r.json()["id"]
    assert await drain_once() == 1

    r = await client.get(f"/api/ext/ocr/jobs/{job_id}?format=hocr", headers=_auth(ocr_token))
    assert r.status_code == 200
    assert "class='ocr_page'" in r.text

    # pdf re-reads the original from storage
    r = await client.get(f"/api/ext/ocr/jobs/{job_id}?format=pdf", headers=_auth(ocr_token))
    assert r.status_code == 200
    assert r.content[:5] == b"%PDF-"

    r = await client.get(f"/api/ext/ocr/jobs/{job_id}?format=docx", headers=_auth(ocr_token))
    assert r.status_code == 422
