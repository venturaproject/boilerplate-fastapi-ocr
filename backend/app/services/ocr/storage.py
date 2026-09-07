"""Filesystem storage for OCR job uploads: {ocr_storage_dir}/{job_id}/{filename}."""

from __future__ import annotations

import os
import shutil
import uuid

import aiofiles

from app.config import settings


def _job_dir(job_id: uuid.UUID) -> str:
    return os.path.join(settings.ocr_storage_dir, str(job_id))


def _safe_name(filename: str | None) -> str:
    name = os.path.basename(filename or "").strip()
    if not name or name in (".", ".."):
        return "upload"
    if len(name) > 200:  # keep well under filesystem NAME_MAX
        root, ext = os.path.splitext(name)
        name = root[: 200 - len(ext)] + ext
    return name


async def save_upload(job_id: uuid.UUID, filename: str | None, data: bytes) -> str:
    job_dir = _job_dir(job_id)
    os.makedirs(job_dir, exist_ok=True)
    path = os.path.join(job_dir, _safe_name(filename))
    async with aiofiles.open(path, "wb") as fh:
        await fh.write(data)
    return path


def read_file(path: str) -> bytes:
    with open(path, "rb") as fh:
        return fh.read()


def delete_job_files(job_id: uuid.UUID) -> None:
    shutil.rmtree(_job_dir(job_id), ignore_errors=True)
