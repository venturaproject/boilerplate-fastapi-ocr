"""Shared logic for the OCR endpoints (external + internal routers)."""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import (
    PayloadTooLargeException,
    UnsupportedMediaException,
    ValidationException,
)
from app.models.ocr_job import OcrJob
from app.repositories import ocr_job as ocr_repo
from app.schemas.ocr import OcrResult
from app.services.ocr import cache as ocr_cache
from app.services.ocr import run_ocr
from app.services.ocr.callback import validate_callback_url
from app.services.ocr.langs import resolve_lang
from app.services.ocr.loader import SUPPORTED_CONTENT_TYPES, normalize_content_type
from app.services.ocr.storage import save_upload

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


async def run_sync_ocr(file: UploadFile, lang: str | None) -> OcrResult:
    content_type = _ensure_supported(file)
    resolved_lang = resolve_lang(lang)
    data = await _read_upload(file, max_bytes=settings.ocr_sync_max_bytes)
    max_pages = settings.ocr_sync_max_pages

    cache_key = ocr_cache.key_for(data, resolved_lang, max_pages)
    cached = ocr_cache.get(cache_key)
    if cached is not None:
        return cached.model_copy(update={"cached": True})

    result = await run_ocr(
        data, content_type, resolved_lang, filename=file.filename, max_pages=max_pages
    )
    ocr_cache.put(cache_key, result)
    return result


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

    return await ocr_repo.create_job(
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
