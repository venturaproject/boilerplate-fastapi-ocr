"""Shared logic for the OCR endpoints (external + internal routers)."""

from __future__ import annotations

import uuid

from fastapi import UploadFile
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
from app.services.ocr import run_ocr
from app.services.ocr.callback import validate_callback_url
from app.services.ocr.loader import SUPPORTED_CONTENT_TYPES, normalize_content_type
from app.services.ocr.storage import save_upload

_UNSUPPORTED_MSG = (
    "Tipo de archivo no soportado. Admitidos: PNG, JPEG, WEBP, BMP, TIFF y PDF."
)


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


def _resolve_lang(lang: str | None) -> str:
    return (lang or settings.ocr_lang).strip() or "es"


async def run_sync_ocr(file: UploadFile, lang: str | None) -> OcrResult:
    _ensure_supported(file)
    data = await _read_upload(file, max_bytes=settings.ocr_sync_max_bytes)
    return await run_ocr(
        data,
        file.content_type,
        lang,
        filename=file.filename,
        max_pages=settings.ocr_sync_max_pages,
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
    data = await _read_upload(file, max_bytes=settings.ocr_max_upload_bytes)
    callback = validate_callback_url(callback_url)

    job_id = uuid.uuid4()
    storage_path = await save_upload(job_id, file.filename, data)

    return await ocr_repo.create_job(
        db,
        job_id=job_id,
        storage_path=storage_path,
        original_filename=file.filename,
        content_type=content_type,
        size_bytes=len(data),
        lang=_resolve_lang(lang),
        callback_url=callback,
        api_client_id=api_client_id,
        created_by_user_id=created_by_user_id,
    )
