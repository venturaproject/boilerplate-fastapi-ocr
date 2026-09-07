"""Orchestrates decoding + OCR inference off the event loop."""

from __future__ import annotations

import functools
import logging
import time

import anyio
import anyio.to_thread

from app.config import settings
from app.exceptions import AppException, OcrEngineException
from app.schemas.ocr import OcrResult
from app.services.ocr.engine import get_engine
from app.services.ocr.loader import load_pages
from app.services.ocr.storage import read_file

logger = logging.getLogger("app.services.ocr")

# Caps concurrent OCR inferences (each runs in a worker thread), per process.
_limiter = anyio.CapacityLimiter(max(1, settings.ocr_max_concurrency))


def _process_sync(
    *,
    data: bytes | None,
    path: str | None,
    content_type: str | None,
    filename: str | None,
    lang: str,
    max_pages: int | None,
) -> OcrResult:
    started = time.perf_counter()
    if data is None:
        assert path is not None, "run_ocr needs either data or path"
        data = read_file(path)  # blocking read, but we're already in a worker thread

    pages = load_pages(data, content_type, filename=filename, max_pages=max_pages)

    engine = get_engine()
    try:
        ocr_pages = engine.recognize_pages(pages, lang)
    except AppException:
        raise
    except Exception as exc:
        logger.exception("Fallo del motor OCR (lang=%s)", lang)
        raise OcrEngineException(f"El motor OCR falló: {type(exc).__name__}") from exc

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
    lang: str,
    *,
    filename: str | None = None,
    max_pages: int | None = None,
) -> OcrResult:
    return await anyio.to_thread.run_sync(
        functools.partial(
            _process_sync,
            data=data,
            path=None,
            content_type=content_type,
            filename=filename,
            lang=lang,
            max_pages=max_pages,
        ),
        limiter=_limiter,
    )


async def run_ocr_file(
    path: str,
    content_type: str | None,
    lang: str,
    *,
    filename: str | None = None,
    max_pages: int | None = None,
) -> OcrResult:
    """Like `run_ocr` but reads the file inside the worker thread (worker/job path)."""
    return await anyio.to_thread.run_sync(
        functools.partial(
            _process_sync,
            data=None,
            path=path,
            content_type=content_type,
            filename=filename,
            lang=lang,
            max_pages=max_pages,
        ),
        limiter=_limiter,
    )
