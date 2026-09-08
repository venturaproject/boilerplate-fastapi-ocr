"""Orchestrates decoding + OCR inference off the event loop."""

from __future__ import annotations

import functools
import logging
import time

import anyio
import anyio.to_thread

from app.config import settings
from app.exceptions import AppException, OcrEngineException
from app.observability import metrics
from app.schemas.ocr import OcrPage, OcrResult
from app.services.ocr.classifier import classify
from app.services.ocr.engine import OcrEngine, get_engine
from app.services.ocr.extractor import extract
from app.services.ocr.langs import allowed_langs, detect_lang
from app.services.ocr.loader import PageImage, load_pages
from app.services.ocr.storage import read_file

logger = logging.getLogger("app.services.ocr")

# Caps concurrent OCR inferences (each runs in a worker thread), per process.
_limiter = anyio.CapacityLimiter(max(1, settings.ocr_max_concurrency))


def _recognize(engine: OcrEngine, pages: list[PageImage], lang: str) -> list[OcrPage]:
    try:
        return engine.recognize_pages(pages, lang)
    except AppException:
        raise
    except Exception as exc:
        logger.exception("Fallo del motor OCR (lang=%s)", lang)
        metrics.record_engine_error(engine.name)
        raise OcrEngineException(f"El motor OCR falló: {type(exc).__name__}") from exc


def _process_sync(
    *,
    data: bytes | None,
    path: str | None,
    content_type: str | None,
    filename: str | None,
    lang: str,
    lang_explicit: bool = True,
    max_pages: int | None,
) -> OcrResult:
    started = time.perf_counter()
    if data is None:
        assert path is not None, "run_ocr needs either data or path"
        data = read_file(path)  # blocking read, but we're already in a worker thread

    pages = load_pages(data, content_type, filename=filename, max_pages=max_pages)

    engine = get_engine()
    ocr_pages = _recognize(engine, pages, lang)
    lang_detected = False

    # Language auto-detection: if the caller didn't pin `lang`, guess it from the
    # text and re-run once with the detected language.
    if not lang_explicit and settings.ocr_lang_autodetect and engine.name != "fake":
        guessed = detect_lang("\n".join(p.text for p in ocr_pages))
        if guessed and guessed != lang and guessed in allowed_langs():
            logger.info("Idioma detectado %s (era %s); reintentando", guessed, lang)
            ocr_pages = _recognize(engine, pages, guessed)
            lang, lang_detected = guessed, True

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    full_text = "\n\n".join(p.text for p in ocr_pages if p.text)
    result = OcrResult(
        engine=engine.name,
        lang=lang,
        lang_detected=lang_detected,
        page_count=len(ocr_pages),
        pages=ocr_pages,
        text=full_text,
        processing_ms=elapsed_ms,
    )
    result.classification = classify(result)
    result.extraction = extract(result)
    return result


async def run_ocr(
    data: bytes,
    content_type: str | None,
    lang: str,
    *,
    filename: str | None = None,
    max_pages: int | None = None,
    lang_explicit: bool = True,
) -> OcrResult:
    return await anyio.to_thread.run_sync(
        functools.partial(
            _process_sync,
            data=data,
            path=None,
            content_type=content_type,
            filename=filename,
            lang=lang,
            lang_explicit=lang_explicit,
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
