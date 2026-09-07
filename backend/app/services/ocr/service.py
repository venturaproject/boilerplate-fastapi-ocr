"""Orchestrates decoding + OCR inference off the event loop."""

from __future__ import annotations

import time

import anyio
import anyio.to_thread

from app.config import settings
from app.schemas.ocr import OcrResult
from app.services.ocr.engine import get_engine
from app.services.ocr.loader import load_pages

# Caps concurrent OCR inferences (each runs in a worker thread).
_limiter = anyio.CapacityLimiter(max(1, settings.ocr_max_concurrency))


def _process_sync(
    data: bytes,
    content_type: str | None,
    filename: str | None,
    lang: str,
    max_pages: int | None,
) -> OcrResult:
    started = time.perf_counter()
    pages = load_pages(data, content_type, filename=filename, max_pages=max_pages)
    engine = get_engine()
    ocr_pages = engine.recognize_pages(pages, lang)
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    full_text = "\n\n".join(p.text for p in ocr_pages if p.text)
    return OcrResult(
        engine=engine.name,
        lang=lang,
        page_count=len(ocr_pages),
        pages=ocr_pages,
        text=full_text,
        processing_ms=elapsed_ms,
    )


async def run_ocr(
    data: bytes,
    content_type: str | None,
    lang: str | None = None,
    *,
    filename: str | None = None,
    max_pages: int | None = None,
) -> OcrResult:
    resolved_lang = (lang or settings.ocr_lang).strip() or "es"
    return await anyio.to_thread.run_sync(
        _process_sync,
        data,
        content_type,
        filename,
        resolved_lang,
        max_pages,
        limiter=_limiter,
    )
