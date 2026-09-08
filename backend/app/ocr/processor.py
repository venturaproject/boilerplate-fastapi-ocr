"""OCR job queue processor — reclaim stragglers, claim pending jobs, run OCR, fire callbacks, purge.

Mirrors the pattern of `app.events.worker` / `app.events.outbox`.
"""

from __future__ import annotations

import logging
import uuid

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.ocr_job import OcrJob
from app.observability import metrics
from app.repositories import client_usage as usage_repo
from app.repositories import document as document_repo
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
        result = await run_ocr_file(storage_path, content_type, lang, filename=filename, max_pages=None)
    except Exception as exc:
        logger.exception("OCR job %s falló", job_id)
        metrics.record_ocr(mode="async", engine=settings.ocr_engine, status="error")
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
                await document_repo.sync_from_job(db, job)
        if status == OcrJob.STATUS_ERROR:
            await _fire_callback(job_id)
        return

    metrics.record_ocr(mode="async", engine=result.engine, status="ok", ms=result.processing_ms)
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
            await document_repo.sync_from_job(db, job)
            if job.api_client_id is not None:
                await usage_repo.increment(db, job.api_client_id, pages=result.page_count, requests=0)
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
            await ocr_repo.record_callback_result(
                db,
                job,
                status,
                max_attempts=settings.ocr_callback_max_attempts,
                backoff_base=settings.ocr_callback_backoff_base_seconds,
            )


async def _deliver_due_callbacks(limit: int = 20) -> int:
    """Retry webhook deliveries whose backoff window has elapsed."""
    async with AsyncSessionLocal() as db, db.begin():
        job_ids = await ocr_repo.claim_due_callbacks(db, limit)
    for job_id in job_ids:
        await _fire_callback(job_id)
    if job_ids:
        logger.info("ocr-worker: %s callback(s) reintentado(s)", len(job_ids))
    return len(job_ids)


async def drain_once(batch_size: int = 5) -> int:
    """Reclaim stragglers, then claim and fully process up to `batch_size` pending jobs."""
    await _reclaim()
    await _deliver_due_callbacks()
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

    async with AsyncSessionLocal() as db, db.begin():
        docs_purged = await document_repo.purge_expired_documents(db, retention_days=settings.document_retention_days)
    if docs_purged:
        logger.info("ocr-worker: %s documento(s) purgado(s) por retención", docs_purged)
    return len(purged)
