from __future__ import annotations

import io

import pymupdf
import pytest
from PIL import Image, ImageDraw

from app.config import settings
from app.exceptions import PayloadTooLargeException, UnsupportedMediaException
from app.services.ocr.pdf_text import extract_pdf_pages

SYNC = "/api/ext/ocr"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _text_page(doc: pymupdf.Document, text: str) -> None:
    doc.new_page().insert_text((72, 720), text, fontsize=12)


def _image_page(doc: pymupdf.Document, label: str = "escaneado") -> None:
    img = Image.new("RGB", (600, 300), "white")
    ImageDraw.Draw(img).text((20, 20), label, fill="black")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    page = doc.new_page(width=600, height=300)
    page.insert_image(page.rect, stream=buf.getvalue())


def _digital_pdf(text: str = "FACTURA 2026\nTOTAL: 100,00 EUR", pages: int = 1) -> bytes:
    doc = pymupdf.open()
    for _ in range(pages):
        _text_page(doc, text)
    return doc.tobytes()


def _scanned_pdf(pages: int = 1) -> bytes:
    doc = pymupdf.open()
    for _ in range(pages):
        _image_page(doc)
    return doc.tobytes()


def _mixed_pdf() -> bytes:
    """3 pages: digital · scanned · digital."""
    doc = pymupdf.open()
    _text_page(doc, "PAGINA UNO texto real\nReferencia ABC-123")
    _image_page(doc)
    _text_page(doc, "PAGINA TRES texto real\nTOTAL 42,00")
    return doc.tobytes()


# ── extract_pdf_pages ────────────────────────────────────────────────────────


def test_reads_the_text_layer():
    pages = extract_pdf_pages(_digital_pdf(pages=2), max_pages=None)
    assert len(pages) == 2
    assert all(p is not None for p in pages)
    assert "TOTAL: 100,00 EUR" in pages[0].text
    line = pages[0].lines[0]
    assert line.confidence == 1.0
    assert len(line.box) == 4


def test_flags_scanned_pages_as_none():
    assert extract_pdf_pages(_scanned_pdf(), max_pages=None) == [None]


def test_mixed_document_marks_only_scanned_pages():
    pages = extract_pdf_pages(_mixed_pdf(), max_pages=None)
    assert [p is None for p in pages] == [False, True, False]
    assert "Referencia ABC-123" in pages[0].text
    assert "TOTAL 42,00" in pages[2].text
    assert pages[0].page == 1 and pages[2].page == 3


def test_min_chars_threshold(monkeypatch):
    monkeypatch.setattr(settings, "ocr_pdf_text_min_chars", 50)
    # "FACTURA 2026\nTOTAL: 100,00 EUR" is ~29 chars → below 50 → treated as scanned
    assert extract_pdf_pages(_digital_pdf(), max_pages=None) == [None]


def test_boxes_are_scaled_to_dpi():
    # An A4 page is 595 pt wide; at OCR_PDF_DPI the pixel width is much larger.
    page = extract_pdf_pages(_digital_pdf(), max_pages=None)[0]
    assert page is not None
    assert page.width > 1000  # pixels, not points
    assert max(pt[0] for pt in page.lines[0].box) <= page.width + 1


def test_respects_max_pages():
    with pytest.raises(PayloadTooLargeException):
        extract_pdf_pages(_digital_pdf(pages=3), max_pages=2)


def test_corrupt_pdf_raises():
    with pytest.raises(UnsupportedMediaException):
        extract_pdf_pages(b"not a pdf at all", max_pages=None)


# ── end-to-end via POST /api/ext/ocr ─────────────────────────────────────────


async def test_sync_digital_pdf_uses_the_text_layer(client, ocr_token):
    r = await client.post(
        SYNC, files={"file": ("invoice.pdf", _digital_pdf(), "application/pdf")}, headers=_auth(ocr_token)
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["engine"] == "pdf-text"
    assert "TOTAL: 100,00 EUR" in body["text"]  # exact, not OCR'd
    assert body["pages"][0]["lines"][0]["confidence"] == 1.0


async def test_sync_scanned_pdf_falls_back_to_the_engine(client, ocr_token):
    r = await client.post(
        SYNC, files={"file": ("scan.pdf", _scanned_pdf(), "application/pdf")}, headers=_auth(ocr_token)
    )
    assert r.status_code == 200, r.text
    assert r.json()["engine"] == "fake"  # the OCR engine in tests


async def test_sync_mixed_pdf_is_hybrid_and_keeps_page_order(client, ocr_token):
    r = await client.post(
        SYNC, files={"file": ("mixed.pdf", _mixed_pdf(), "application/pdf")}, headers=_auth(ocr_token)
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["engine"] == "fake+pdf-text"
    assert body["page_count"] == 3
    pages = body["pages"]
    assert [p["page"] for p in pages] == [1, 2, 3]
    assert "Referencia ABC-123" in pages[0]["text"]  # text layer
    assert "[fake-ocr" in pages[1]["text"] and "page 2" in pages[1]["text"]  # OCR'd
    assert "TOTAL 42,00" in pages[2]["text"]  # text layer


async def test_text_layer_can_be_disabled(client, ocr_token, monkeypatch):
    monkeypatch.setattr(settings, "ocr_pdf_text_layer", False)
    r = await client.post(
        SYNC, files={"file": ("invoice.pdf", _digital_pdf(), "application/pdf")}, headers=_auth(ocr_token)
    )
    assert r.status_code == 200
    assert r.json()["engine"] == "fake"


@pytest.mark.parametrize("fmt", ["text", "hocr", "alto", "pdf"])
async def test_output_formats_on_a_digital_pdf(client, ocr_token, fmt):
    r = await client.post(
        f"{SYNC}?format={fmt}",
        files={"file": ("invoice.pdf", _digital_pdf(), "application/pdf")},
        headers=_auth(ocr_token),
    )
    assert r.status_code == 200, r.text
    if fmt == "pdf":
        assert r.content[:5] == b"%PDF-"
    elif fmt == "text":
        assert "TOTAL: 100,00 EUR" in r.text
    else:
        assert b"<" in r.content  # well-formed XML/XHTML
