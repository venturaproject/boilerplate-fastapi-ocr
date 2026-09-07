"""OCR job queue processor — reclaim stragglers, claim pending jobs, run OCR, fire callbacks, purge.

Mirrors the pattern of `app.events.worker` / `app.events.outbox`.
"""

from __future__ import annotations

import logging
import uuid

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.ocr_job import OcrJob
from app.repositories import ocr_job as ocr_repo
from app.schemas.ocr import OcrJobOut
from app.services.ocr import run_ocr_file
from app.services.ocr.callback import deliver as deliver_callback
from app.services.ocr.langs import resolve_lang
from app.services.ocr.storage import delete_job_files

logger = logging.getLogger("app.ocr.worker")


async def _reclaim() -> int:
    async with AsyncSessionLocal() as db, db.begin():
        return await ocr_repo.reclaim_stale_jobs(
            db,
            stale_seconds=settings.ocr_job_stale_seconds,
            max_attempts=settings.ocr_job_max_attempts,
        )


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
        lang = resolve_lang(job.lang)

    try:
        result = await run_ocr_file(
            storage_path, content_type, lang, filename=filename, max_pages=None
        )
    except Exception as exc:
        logger.exception("OCR job %s falló", job_id)
        async with AsyncSessionLocal() as db, db.begin():
            job = await ocr_repo.get_job(db, job_id)
            if job is None:
                return
            status = await ocr_repo.mark_failed(
                db,
                job,
                error=f"{type(exc).__name__}: {exc}",
                max_attempts=settings.ocr_job_max_attempts,
            )
        if status == OcrJob.STATUS_ERROR:
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
                processing_ms=result.processing_ms,
                doc_type=result.classification.doc_type if result.classification else None,
            )
    await _fire_callback(job_id)


async def _fire_callback(job_id: uuid.UUID) -> None:
    async with AsyncSessionLocal() as db:
        job = await ocr_repo.get_job(db, job_id)
        if job is None or not job.callback_url:
            return
        url = job.callback_url
        payload = OcrJobOut.model_validate(job).model_dump(mode="json")

    status = await deliver_callback(url, payload)

    async with AsyncSessionLocal() as db, db.begin():
        job = await ocr_repo.get_job(db, job_id)
        if job is not None:
            await ocr_repo.set_callback_status(db, job, status)


async def drain_once(batch_size: int = 5) -> int:
    """Reclaim stragglers, then claim and fully process up to `batch_size` pending jobs."""
    await _reclaim()
    job_ids = await _claim(batch_size)
    for job_id in job_ids:
        await _process_one(job_id)
    return len(job_ids)


async def purge_once() -> int:
    """Delete finished jobs (and their files) older than the retention window."""
    async with AsyncSessionLocal() as db, db.begin():
        purged = await ocr_repo.purge_expired_jobs(db, retention_days=settings.ocr_job_retention_days)
    for job_id in purged:
        delete_job_files(job_id)
    if purged:
        logger.info("ocr-worker: %s job(s) purgado(s) por retención", len(purged))
    return len(purged)
