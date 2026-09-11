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
from app.services.ocr.loader import PDF_CONTENT_TYPES, PageImage, load_pages, normalize_content_type
from app.services.ocr.pdf_text import extract_pdf_pages
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
    extractor_mode: str | None = None,
) -> OcrResult:
    started = time.perf_counter()
    if data is None:
        assert path is not None, "run_ocr needs either data or path"
        data = read_file(path)  # blocking read, but we're already in a worker thread

    engine = get_engine()
    lang_detected = False
    is_pdf = normalize_content_type(content_type, filename) in PDF_CONTENT_TYPES

    text_pages: list[OcrPage | None] = []
    if is_pdf and settings.ocr_pdf_text_layer:
        text_pages = extract_pdf_pages(data, max_pages=max_pages)

    if text_pages and any(tp is not None for tp in text_pages):
        # Text-first: use the embedded text layer, OCR only the pages without one.
        need_ocr = [i for i, tp in enumerate(text_pages) if tp is None]
        engine_name = "pdf-text"
        ocr_of_images: list[OcrPage] = []
        if need_ocr:
            images = load_pages(data, content_type, filename=filename, max_pages=max_pages)
            to_ocr = [images[i] for i in need_ocr]
            ocr_of_images = _recognize(engine, to_ocr, lang)
            engine_name = f"{engine.name}+pdf-text"
            if not lang_explicit and settings.ocr_lang_autodetect and engine.name != "fake":
                guessed = detect_lang("\n".join(p.text for p in ocr_of_images))
                if guessed and guessed != lang and guessed in allowed_langs():
                    logger.info("Idioma detectado %s (era %s); reintentando", guessed, lang)
                    ocr_of_images = _recognize(engine, to_ocr, guessed)
                    lang, lang_detected = guessed, True
        it = iter(ocr_of_images)
        ocr_pages = [tp if tp is not None else next(it) for tp in text_pages]
    else:
        pages = load_pages(data, content_type, filename=filename, max_pages=max_pages)
        engine_name = engine.name
        ocr_pages = _recognize(engine, pages, lang)
        # Language auto-detection: if the caller didn't pin `lang`, guess it from
        # the text and re-run once with the detected language.
        if not lang_explicit and settings.ocr_lang_autodetect and engine.name != "fake":
            guessed = detect_lang("\n".join(p.text for p in ocr_pages))
            if guessed and guessed != lang and guessed in allowed_langs():
                logger.info("Idioma detectado %s (era %s); reintentando", guessed, lang)
                ocr_pages = _recognize(engine, pages, guessed)
                lang, lang_detected = guessed, True

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    full_text = "\n\n".join(p.text for p in ocr_pages if p.text)
    result = OcrResult(
        engine=engine_name,
        lang=lang,
        lang_detected=lang_detected,
        page_count=len(ocr_pages),
        pages=ocr_pages,
        text=full_text,
        processing_ms=elapsed_ms,
    )
    result.classification = classify(result)
    result.extraction = extract(result, mode_override=extractor_mode)
    return result


async def run_ocr(
    data: bytes,
    content_type: str | None,
    lang: str,
    *,
    filename: str | None = None,
    max_pages: int | None = None,
    lang_explicit: bool = True,
    extractor_mode: str | None = None,
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
            extractor_mode=extractor_mode,
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
    extractor_mode: str | None = None,
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
            extractor_mode=extractor_mode,
        ),
        limiter=_limiter,
    )
