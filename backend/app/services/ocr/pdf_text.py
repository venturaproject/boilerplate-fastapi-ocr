"""Text-first PDF handling: pull the embedded text layer straight from the PDF
(exact, fast, no OCR) and only fall back to rasterize + OCR for pages that have
little or no real text (scanned PDFs).

Coordinates are scaled to `ocr_pdf_dpi` so the boxes line up with the image-OCR
path and with the searchable-PDF renderer.
"""

from __future__ import annotations

import logging

from app.config import settings
from app.exceptions import PayloadTooLargeException, UnsupportedMediaException
from app.schemas.ocr import OcrLine, OcrPage
from app.services.ocr.engine import _sort_reading_order

logger = logging.getLogger("app.services.ocr")


def extract_pdf_pages(data: bytes, *, max_pages: int | None) -> list[OcrPage | None]:
    """One entry per PDF page: an `OcrPage` built from the text layer, or `None`
    if the page needs OCR. Empty list if PyMuPDF is unavailable."""
    try:
        import pymupdf as fitz
    except ImportError:  # pragma: no cover
        return []

    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise UnsupportedMediaException("No se pudo leer el PDF") from exc

    zoom = settings.ocr_pdf_dpi / 72.0
    min_chars = settings.ocr_pdf_text_min_chars
    out: list[OcrPage | None] = []
    with doc:
        if max_pages is not None and doc.page_count > max_pages:
            raise PayloadTooLargeException(
                f"El PDF tiene {doc.page_count} páginas; el máximo permitido es {max_pages}."
            )
        for i in range(doc.page_count):
            page = doc.load_page(i)
            raw = page.get_text("dict")
            plain = page.get_text("text").strip()
            if len(plain) < min_chars:
                out.append(None)  # scanned / near-empty page → OCR it
                continue

            width = round(page.rect.width * zoom)
            height = round(page.rect.height * zoom)
            lines: list[OcrLine] = []
            for block in raw.get("blocks", []):
                for ln in block.get("lines", []):
                    spans = ln.get("spans", [])
                    text = "".join(s.get("text", "") for s in spans).strip()
                    if not text:
                        continue
                    x0, y0, x1, y1 = ln.get("bbox", (0, 0, 0, 0))
                    box = [
                        [x0 * zoom, y0 * zoom],
                        [x1 * zoom, y0 * zoom],
                        [x1 * zoom, y1 * zoom],
                        [x0 * zoom, y1 * zoom],
                    ]
                    lines.append(OcrLine(text=text, confidence=1.0, box=box))

            lines = _sort_reading_order(lines)
            out.append(
                OcrPage(
                    page=i + 1,
                    width=width,
                    height=height,
                    lines=lines,
                    text="\n".join(ln.text for ln in lines),
                )
            )
    return out
