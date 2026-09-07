"""OCR job queue processor — claims pending jobs, runs OCR, fires callbacks.

Mirrors the pattern of `app.events.worker` / `app.events.outbox`.
"""

from __future__ import annotations

import logging
import uuid

import httpx

from app.config import settings
from app.database import AsyncSessionLocal
from app.repositories import ocr_job as ocr_repo
from app.schemas.ocr import OcrJobOut
from app.services.ocr import run_ocr
from app.services.ocr.storage import read_file

logger = logging.getLogger("app.ocr.worker")


async def _claim(batch_size: int) -> list[uuid.UUID]:
    async with AsyncSessionLocal() as db, db.begin():
        jobs = await ocr_repo.claim_pending_jobs(db, batch_size)
        return [job.id for job in jobs]


async def _process_one(job_id: uuid.UUID) -> None:
    async with AsyncSessionLocal() as db:
        job = await ocr_repo.get_job(db, job_id)
        if job is None:
            return
        storage_path = job.storage_path
        content_type = job.content_type
        filename = job.original_filename
        lang = job.lang

    try:
        data = read_file(storage_path)
        result = await run_ocr(data, content_type, lang, filename=filename, max_pages=None)
    except Exception as exc:
        logger.exception("OCR job %s failed", job_id)
        async with AsyncSessionLocal() as db, db.begin():
            job = await ocr_repo.get_job(db, job_id)
            if job is not None:
                await ocr_repo.mark_error(db, job, error=f"{type(exc).__name__}: {exc}")
        await _fire_callback(job_id)
        return

    async with AsyncSessionLocal() as db, db.begin():
        job = await ocr_repo.get_job(db, job_id)
        if job is not None:
            await ocr_repo.mark_done(
                db,
                job,
                result=result.model_dump(mode="json"),
                page_count=result.page_count,
            )
    await _fire_callback(job_id)


async def _fire_callback(job_id: uuid.UUID) -> None:
    async with AsyncSessionLocal() as db:
        job = await ocr_repo.get_job(db, job_id)
        if job is None or not job.callback_url:
            return
        url = job.callback_url
        payload = OcrJobOut.model_validate(job).model_dump(mode="json")

    status = "unsent"
    try:
        async with httpx.AsyncClient(timeout=settings.ocr_callback_timeout_seconds) as client:
            for _attempt in range(2):
                try:
                    resp = await client.post(url, json=payload)
                    status = f"http_{resp.status_code}"
                    if resp.is_success:
                        break
                except httpx.HTTPError as exc:
                    status = f"error:{type(exc).__name__}"
    finally:
        async with AsyncSessionLocal() as db, db.begin():
            job = await ocr_repo.get_job(db, job_id)
            if job is not None:
                await ocr_repo.set_callback_status(db, job, status)


async def drain_once(batch_size: int = 5) -> int:
    """Claim and fully process up to `batch_size` pending jobs. Returns how many were claimed."""
    job_ids = await _claim(batch_size)
    for job_id in job_ids:
        await _process_one(job_id)
    return len(job_ids)
