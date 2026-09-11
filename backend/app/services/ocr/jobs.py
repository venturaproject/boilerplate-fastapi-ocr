"""Shared logic for the OCR endpoints (external + internal routers)."""

from __future__ import annotations

import io
import logging
import uuid
import zipfile
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

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
from app.observability import metrics
from app.repositories import document as document_repo
from app.repositories import ocr_job as ocr_repo
from app.schemas.ocr import ClassifyOut, OcrResult
from app.services.ocr import cache as ocr_cache
from app.services.ocr import run_ocr
from app.services.ocr.callback import validate_callback_url
from app.services.ocr.extractor import resolve_mode as resolve_extractor_mode
from app.services.ocr.langs import resolve_lang
from app.services.ocr.loader import SUPPORTED_CONTENT_TYPES, normalize_content_type
from app.services.ocr.storage import save_upload

logger = logging.getLogger("app.services.ocr.jobs")

_UNSUPPORTED_MSG = "Tipo de archivo no soportado. Admitidos: PNG, JPEG, WEBP, BMP, TIFF y PDF."


def content_length_guard(max_bytes: int) -> Callable[[Request], Awaitable[None]]:
    """Reject oversized uploads from the Content-Length header before buffering the body."""
    envelope_slack = max_bytes // 100 + 8192

    async def dep(request: Request) -> None:
        raw = request.headers.get("content-length")
        if raw and raw.isdigit() and int(raw) > max_bytes + envelope_slack:
            raise PayloadTooLargeException(f"La petición pesa {raw} bytes; el máximo permitido es ~{max_bytes}.")

    return dep


_ZIP_MAX_RATIO = 200  # reject entries that expand > 200x (42.zip-style bombs)


def _expand_zip(raw: bytes) -> list[tuple[str, bytes, str]]:
    """Expand a .zip into (name, bytes, content_type) for supported entries, with
    anti-bomb caps: per-entry size, total size, entry count, compression ratio."""
    per_entry = settings.ocr_max_upload_bytes
    total_cap = settings.ocr_batch_max_total_bytes
    out: list[tuple[str, bytes, str]] = []
    total = 0
    try:
        zf = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile as exc:
        raise ValidationException("El .zip está corrupto.") from exc
    with zf:
        members = [i for i in zf.infolist() if not i.is_dir()]
        if len(members) > settings.ocr_batch_max_files:
            raise PayloadTooLargeException(
                f"El .zip tiene {len(members)} entradas; el máximo es {settings.ocr_batch_max_files}."
            )
        for info in members:
            if info.compress_size and info.file_size / info.compress_size > _ZIP_MAX_RATIO:
                raise PayloadTooLargeException(f"Entrada '{info.filename}' con ratio de compresión sospechoso.")
            ct = normalize_content_type(None, info.filename)
            if ct not in SUPPORTED_CONTENT_TYPES:
                continue
            with zf.open(info) as src:
                data = src.read(per_entry + 1)  # decompress at most per_entry (+1 to detect overflow)
            if len(data) > per_entry:
                raise PayloadTooLargeException(f"Entrada '{info.filename}' supera el máximo de {per_entry} bytes.")
            total += len(data)
            if total > total_cap:
                raise PayloadTooLargeException(f"El .zip descomprimido supera {total_cap} bytes.")
            out.append((info.filename, data, ct))
    return out


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
        raise PayloadTooLargeException(f"El archivo pesa {len(data)} bytes; el máximo permitido es {max_bytes}.")
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
    data: bytes = b""


@dataclass
class FormattedResult:
    body: bytes
    media_type: str


async def _record_document(mode: str, **kwargs: Any) -> None:
    """Persist a `documents` row for an OCR call. A write error is logged, never raised."""
    try:
        async with AsyncSessionLocal() as db, db.begin():
            await document_repo.record_document(db, mode=mode, **kwargs)
    except Exception:
        logger.exception("No se pudo registrar el documento OCR (mode=%s)", mode)


async def _record_usage(api_client_id: uuid.UUID | None, *, pages: int, requests: int = 1) -> None:
    if api_client_id is None:
        return
    try:
        from app.repositories import client_usage as usage_repo

        async with AsyncSessionLocal() as db, db.begin():
            await usage_repo.increment(db, api_client_id, pages=pages, requests=requests)
    except Exception:
        logger.exception("No se pudo registrar el uso del cliente %s", api_client_id)


async def _record_processed(
    mode: str,
    result: OcrResult,
    meta: _UploadMeta,
    *,
    api_client_id: uuid.UUID | None,
    created_by_user_id: uuid.UUID | None,
) -> None:
    metrics.record_ocr(mode=mode, engine=result.engine, status="ok", ms=result.processing_ms)
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
        extraction=result.extraction.model_dump(mode="json") if result.extraction else None,
    )
    await _record_usage(api_client_id, pages=result.page_count)


async def _sync_ocr(
    file: UploadFile, lang: str | None, *, extractor_mode: str | None = None
) -> tuple[OcrResult, _UploadMeta]:
    content_type = _ensure_supported(file)
    resolved_lang = resolve_lang(lang)
    data = await _read_upload(file, max_bytes=settings.ocr_sync_max_bytes)
    max_pages = settings.ocr_sync_max_pages
    meta = _UploadMeta(
        filename=file.filename,
        content_type=content_type,
        size_bytes=len(data),
        lang=resolved_lang,
        data=data,
    )

    # Keyed by the *resolved* mode, not the raw override: two calls that land on the same
    # effective mode (e.g. both inheriting the current global OCR_EXTRACTOR) share a cache
    # entry; two that don't (different overrides, or the global setting changed) don't.
    cache_key = ocr_cache.key_for(data, resolved_lang, max_pages, resolve_extractor_mode(extractor_mode))
    cached = ocr_cache.get(cache_key)
    if cached is not None:
        return cached.model_copy(update={"cached": True}), meta

    result = await run_ocr(
        data,
        content_type,
        resolved_lang,
        filename=file.filename,
        max_pages=max_pages,
        lang_explicit=lang is not None,
        extractor_mode=extractor_mode,
    )
    ocr_cache.put(cache_key, result)
    return result, meta


async def run_sync_ocr(
    file: UploadFile,
    lang: str | None,
    *,
    fmt: str = "json",
    api_client_id: uuid.UUID | None = None,
    created_by_user_id: uuid.UUID | None = None,
    extractor_mode: str | None = None,
) -> OcrResult | FormattedResult:
    result, meta = await _sync_ocr(file, lang, extractor_mode=extractor_mode)
    await _record_processed(
        Document.MODE_SYNC,
        result,
        meta,
        api_client_id=api_client_id,
        created_by_user_id=created_by_user_id,
    )
    if fmt == "json":
        return result
    return _render(result, fmt, meta)


def _render(result: OcrResult, fmt: str, meta: _UploadMeta) -> FormattedResult:
    from app.services.ocr import formats
    from app.services.ocr.loader import load_pages

    if fmt not in formats.FORMATS:
        raise ValidationException(f"format inválido: {fmt}. Admitidos: {', '.join(formats.FORMATS)}.")
    pages = None
    if fmt == "pdf":
        pages = load_pages(
            meta.data,
            meta.content_type,
            filename=meta.filename,
            max_pages=settings.ocr_sync_max_pages,
        )
    body, media_type = formats.render(result, fmt, pages)
    return FormattedResult(body=body, media_type=media_type)


async def classify_document(
    file: UploadFile,
    lang: str | None,
    *,
    api_client_id: uuid.UUID | None = None,
    created_by_user_id: uuid.UUID | None = None,
    extractor_mode: str | None = None,
) -> ClassifyOut:
    result, meta = await _sync_ocr(file, lang, extractor_mode=extractor_mode)
    await _record_processed(
        Document.MODE_CLASSIFY,
        result,
        meta,
        api_client_id=api_client_id,
        created_by_user_id=created_by_user_id,
    )
    c = result.classification
    excerpt = result.text[:500]
    if settings.document_redact_pii:
        from app.services.ocr.redact import redact_pii

        excerpt = redact_pii(excerpt)
    return ClassifyOut(
        doc_type=c.doc_type if c else None,
        confidence=c.confidence if c else 0.0,
        scores=c.scores if c else {},
        lang=result.lang,
        page_count=result.page_count,
        text_excerpt=excerpt,
        extraction=result.extraction,
    )


async def _create_job_from_bytes(
    db: AsyncSession,
    *,
    filename: str | None,
    content_type: str,
    data: bytes,
    lang: str,
    callback_url: str | None,
    api_client_id: uuid.UUID | None,
    created_by_user_id: uuid.UUID | None,
    batch_id: uuid.UUID | None,
) -> OcrJob:
    job_id = uuid.uuid4()
    storage_path = await save_upload(job_id, filename, data)
    job = await ocr_repo.create_job(
        db,
        job_id=job_id,
        storage_path=storage_path,
        original_filename=_clean_filename(filename),
        content_type=content_type,
        size_bytes=len(data),
        lang=lang,
        callback_url=callback_url,
        api_client_id=api_client_id,
        created_by_user_id=created_by_user_id,
        batch_id=batch_id,
    )
    await document_repo.record_document(
        db,
        mode=Document.MODE_ASYNC,
        status=Document.STATUS_PENDING,
        ocr_job_id=job.id,
        api_client_id=api_client_id,
        created_by_user_id=created_by_user_id,
        original_filename=_clean_filename(filename),
        content_type=content_type,
        size_bytes=len(data),
        lang=lang,
    )
    if api_client_id is not None:
        from app.repositories import client_usage as usage_repo

        await usage_repo.increment(db, api_client_id, pages=0, requests=1)
    return job


async def create_ocr_job(
    db: AsyncSession,
    file: UploadFile,
    *,
    lang: str | None,
    callback_url: str | None = None,
    api_client_id: uuid.UUID | None = None,
    created_by_user_id: uuid.UUID | None = None,
    batch_id: uuid.UUID | None = None,
) -> OcrJob:
    content_type = _ensure_supported(file)
    resolved_lang = resolve_lang(lang)
    callback = validate_callback_url(callback_url)
    data = await _read_upload(file, max_bytes=settings.ocr_max_upload_bytes)
    return await _create_job_from_bytes(
        db,
        filename=file.filename,
        content_type=content_type,
        data=data,
        lang=resolved_lang,
        callback_url=callback,
        api_client_id=api_client_id,
        created_by_user_id=created_by_user_id,
        batch_id=batch_id,
    )


async def create_batch_jobs(
    db: AsyncSession,
    files: list[UploadFile],
    *,
    lang: str | None,
    callback_url: str | None = None,
    api_client_id: uuid.UUID | None = None,
    created_by_user_id: uuid.UUID | None = None,
) -> tuple[uuid.UUID, list[OcrJob]]:
    """Create N jobs sharing a batch_id. A single .zip is expanded into its entries."""
    resolved_lang = resolve_lang(lang)
    callback = validate_callback_url(callback_url)
    batch_id = uuid.uuid4()

    entries: list[tuple[str | None, bytes, str]] = []
    for f in files:
        raw = await _read_upload(f, max_bytes=settings.ocr_max_upload_bytes)
        if (f.content_type or "").endswith("zip") or (f.filename or "").lower().endswith(".zip"):
            entries.extend(_expand_zip(raw))
        else:
            entries.append((f.filename, raw, _ensure_supported(f)))

    if not entries:
        raise ValidationException("El lote no contiene archivos soportados.")
    if len(entries) > settings.ocr_batch_max_files:
        raise PayloadTooLargeException(
            f"El lote tiene {len(entries)} archivos; el máximo es {settings.ocr_batch_max_files}."
        )

    jobs = [
        await _create_job_from_bytes(
            db,
            filename=name,
            content_type=ct,
            data=blob,
            lang=resolved_lang,
            callback_url=callback,
            api_client_id=api_client_id,
            created_by_user_id=created_by_user_id,
            batch_id=batch_id,
        )
        for name, blob, ct in entries
    ]
    return batch_id, jobs
