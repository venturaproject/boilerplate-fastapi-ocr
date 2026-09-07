"""Shared logic for the OCR endpoints (external + internal routers)."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from fastapi import Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.exceptions import (
    PayloadTooLargeException,
    UnsupportedMediaException,
    ValidationException,
)
from app.models.document import Document
from app.models.ocr_job import OcrJob
from app.repositories import document as document_repo
from app.repositories import ocr_job as ocr_repo
from app.schemas.ocr import ClassifyOut, OcrResult
from app.services.ocr import cache as ocr_cache
from app.services.ocr import run_ocr
from app.services.ocr.callback import validate_callback_url
from app.services.ocr.langs import resolve_lang
from app.services.ocr.loader import SUPPORTED_CONTENT_TYPES, normalize_content_type
from app.services.ocr.storage import save_upload

logger = logging.getLogger("app.services.ocr.jobs")

_UNSUPPORTED_MSG = (
    "Tipo de archivo no soportado. Admitidos: PNG, JPEG, WEBP, BMP, TIFF y PDF."
)


def content_length_guard(max_bytes: int) -> Callable[[Request], Awaitable[None]]:
    """Reject oversized uploads from the Content-Length header before buffering the body."""
    envelope_slack = max_bytes // 100 + 8192

    async def dep(request: Request) -> None:
        raw = request.headers.get("content-length")
        if raw and raw.isdigit() and int(raw) > max_bytes + envelope_slack:
            raise PayloadTooLargeException(
                f"La petición pesa {raw} bytes; el máximo permitido es ~{max_bytes}."
            )

    return dep


def _ensure_supported(file: UploadFile) -> str:
    ct = normalize_content_type(file.content_type, file.filename)
    if ct not in SUPPORTED_CONTENT_TYPES:
        raise UnsupportedMediaException(_UNSUPPORTED_MSG)
    return ct


async def _read_upload(file: UploadFile, *, max_bytes: int) -> bytes:
    data = await file.read()
    if not data:
        raise ValidationException("El archivo está vacío.")
    if len(data) > max_bytes:
        raise PayloadTooLargeException(
            f"El archivo pesa {len(data)} bytes; el máximo permitido es {max_bytes}."
        )
    return data


def _clean_filename(name: str | None) -> str | None:
    if not name:
        return None
    return name[:512]


@dataclass
class _UploadMeta:
    filename: str | None
    content_type: str
    size_bytes: int
    lang: str


async def _record_document(mode: str, **kwargs) -> None:
    """Persist a `documents` row for an OCR call. A write error is logged, never raised."""
    try:
        async with AsyncSessionLocal() as db, db.begin():
            await document_repo.record_document(db, mode=mode, **kwargs)
    except Exception:
        logger.exception("No se pudo registrar el documento OCR (mode=%s)", mode)


async def _record_processed(
    mode: str,
    result: OcrResult,
    meta: _UploadMeta,
    *,
    api_client_id: uuid.UUID | None,
    created_by_user_id: uuid.UUID | None,
) -> None:
    c = result.classification
    await _record_document(
        mode,
        status=Document.STATUS_DONE,
        api_client_id=api_client_id,
        created_by_user_id=created_by_user_id,
        original_filename=_clean_filename(meta.filename),
        content_type=meta.content_type,
        size_bytes=meta.size_bytes,
        lang=meta.lang,
        page_count=result.page_count,
        processing_ms=result.processing_ms,
        doc_type=c.doc_type if c else None,
        doc_type_confidence=c.confidence if c and c.doc_type else None,
        text=result.text,
    )


async def _sync_ocr(file: UploadFile, lang: str | None) -> tuple[OcrResult, _UploadMeta]:
    content_type = _ensure_supported(file)
    resolved_lang = resolve_lang(lang)
    data = await _read_upload(file, max_bytes=settings.ocr_sync_max_bytes)
    max_pages = settings.ocr_sync_max_pages
    meta = _UploadMeta(
        filename=file.filename,
        content_type=content_type,
        size_bytes=len(data),
        lang=resolved_lang,
    )

    cache_key = ocr_cache.key_for(data, resolved_lang, max_pages)
    cached = ocr_cache.get(cache_key)
    if cached is not None:
        return cached.model_copy(update={"cached": True}), meta

    result = await run_ocr(
        data, content_type, resolved_lang, filename=file.filename, max_pages=max_pages
    )
    ocr_cache.put(cache_key, result)
    return result, meta


async def run_sync_ocr(
    file: UploadFile,
    lang: str | None,
    *,
    api_client_id: uuid.UUID | None = None,
    created_by_user_id: uuid.UUID | None = None,
) -> OcrResult:
    result, meta = await _sync_ocr(file, lang)
    await _record_processed(
        Document.MODE_SYNC,
        result,
        meta,
        api_client_id=api_client_id,
        created_by_user_id=created_by_user_id,
    )
    return result


async def classify_document(
    file: UploadFile,
    lang: str | None,
    *,
    api_client_id: uuid.UUID | None = None,
    created_by_user_id: uuid.UUID | None = None,
) -> ClassifyOut:
    result, meta = await _sync_ocr(file, lang)
    await _record_processed(
        Document.MODE_CLASSIFY,
        result,
        meta,
        api_client_id=api_client_id,
        created_by_user_id=created_by_user_id,
    )
    c = result.classification
    return ClassifyOut(
        doc_type=c.doc_type if c else None,
        confidence=c.confidence if c else 0.0,
        scores=c.scores if c else {},
        lang=result.lang,
        page_count=result.page_count,
        text_excerpt=result.text[:500],
    )


async def create_ocr_job(
    db: AsyncSession,
    file: UploadFile,
    *,
    lang: str | None,
    callback_url: str | None = None,
    api_client_id: uuid.UUID | None = None,
    created_by_user_id: uuid.UUID | None = None,
) -> OcrJob:
    content_type = _ensure_supported(file)
    resolved_lang = resolve_lang(lang)
    callback = validate_callback_url(callback_url)
    data = await _read_upload(file, max_bytes=settings.ocr_max_upload_bytes)

    job_id = uuid.uuid4()
    storage_path = await save_upload(job_id, file.filename, data)

    job = await ocr_repo.create_job(
        db,
        job_id=job_id,
        storage_path=storage_path,
        original_filename=_clean_filename(file.filename),
        content_type=content_type,
        size_bytes=len(data),
        lang=resolved_lang,
        callback_url=callback,
        api_client_id=api_client_id,
        created_by_user_id=created_by_user_id,
    )

    # Register the document in the same transaction as the job it mirrors.
    await document_repo.record_document(
        db,
        mode=Document.MODE_ASYNC,
        status=Document.STATUS_PENDING,
        ocr_job_id=job.id,
        api_client_id=api_client_id,
        created_by_user_id=created_by_user_id,
        original_filename=_clean_filename(file.filename),
        content_type=content_type,
        size_bytes=len(data),
        lang=resolved_lang,
    )
    return job
