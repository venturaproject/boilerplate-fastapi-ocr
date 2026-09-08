from __future__ import annotations

import io

import pymupdf
from PIL import Image, ImageDraw

from app.services.ocr.pdf_text import extract_pdf_pages

SYNC = "/api/ext/ocr"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _digital_pdf(text: str = "FACTURA 2026\nTOTAL: 100,00 EUR", pages: int = 1) -> bytes:
    doc = pymupdf.open()
    for _ in range(pages):
        page = doc.new_page()
        page.insert_text((72, 720), text, fontsize=12)
    return doc.tobytes()


def _scanned_pdf() -> bytes:
    img = Image.new("RGB", (600, 300), "white")
    ImageDraw.Draw(img).text((20, 20), "escaneado", fill="black")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    doc = pymupdf.open()
    page = doc.new_page(width=600, height=300)
    page.insert_image(page.rect, stream=buf.getvalue())
    return doc.tobytes()


def test_extract_pdf_pages_reads_the_text_layer():
    pages = extract_pdf_pages(_digital_pdf(pages=2), max_pages=None)
    assert len(pages) == 2
    assert all(p is not None for p in pages)
    assert "TOTAL: 100,00 EUR" in pages[0].text
    line = pages[0].lines[0]
    assert line.confidence == 1.0
    assert len(line.box) == 4


def test_extract_pdf_pages_flags_scanned_pages_as_none():
    pages = extract_pdf_pages(_scanned_pdf(), max_pages=None)
    assert pages == [None]


async def test_sync_digital_pdf_uses_the_text_layer(client, ocr_token):
    files = {"file": ("invoice.pdf", _digital_pdf(), "application/pdf")}
    r = await client.post(SYNC, files=files, headers=_auth(ocr_token))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["engine"] == "pdf-text"
    assert "TOTAL: 100,00 EUR" in body["text"]  # exact, not OCR'd


async def test_sync_scanned_pdf_falls_back_to_the_engine(client, ocr_token):
    files = {"file": ("scan.pdf", _scanned_pdf(), "application/pdf")}
    r = await client.post(SYNC, files=files, headers=_auth(ocr_token))
    assert r.status_code == 200, r.text
    assert r.json()["engine"] != "pdf-text"  # OCR engine (fake in tests)


async def test_text_layer_can_be_disabled(client, ocr_token, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "ocr_pdf_text_layer", False)
    files = {"file": ("invoice.pdf", _digital_pdf(), "application/pdf")}
    r = await client.post(SYNC, files=files, headers=_auth(ocr_token))
    assert r.status_code == 200
    assert r.json()["engine"] != "pdf-text"
