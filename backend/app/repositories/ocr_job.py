import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ocr_job import OcrJob


async def create_job(
    db: AsyncSession,
    *,
    job_id: uuid.UUID | None = None,
    storage_path: str,
    original_filename: str | None,
    content_type: str | None,
    size_bytes: int,
    lang: str,
    callback_url: str | None = None,
    api_client_id: uuid.UUID | None = None,
    created_by_user_id: uuid.UUID | None = None,
) -> OcrJob:
    job = OcrJob(
        id=job_id or uuid.uuid4(),
        storage_path=storage_path,
        original_filename=original_filename,
        content_type=content_type,
        size_bytes=size_bytes,
        lang=lang,
        callback_url=callback_url,
        api_client_id=api_client_id,
        created_by_user_id=created_by_user_id,
        status=OcrJob.STATUS_PENDING,
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)
    return job


async def get_job(
    db: AsyncSession,
    job_id: uuid.UUID,
    *,
    api_client_id: uuid.UUID | None = None,
) -> OcrJob | None:
    stmt = select(OcrJob).where(OcrJob.id == job_id)
    if api_client_id is not None:
        stmt = stmt.where(OcrJob.api_client_id == api_client_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_jobs(
    db: AsyncSession,
    *,
    api_client_id: uuid.UUID | None = None,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[OcrJob], int]:
    filters = []
    if api_client_id is not None:
        filters.append(OcrJob.api_client_id == api_client_id)

    total = (
        await db.execute(select(func.count()).select_from(OcrJob).where(*filters))
    ).scalar_one()

    result = await db.execute(
        select(OcrJob)
        .where(*filters)
        .order_by(OcrJob.created_at.desc())
        .limit(per_page)
        .offset((page - 1) * per_page)
    )
    return list(result.scalars().all()), int(total)


async def claim_pending_jobs(db: AsyncSession, limit: int) -> list[OcrJob]:
    """Atomically pick up pending jobs and mark them processing (FOR UPDATE SKIP LOCKED)."""
    result = await db.execute(
        select(OcrJob)
        .where(OcrJob.status == OcrJob.STATUS_PENDING)
        .order_by(OcrJob.created_at)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    jobs = list(result.scalars().all())
    now = datetime.now(tz=UTC)
    for job in jobs:
        job.status = OcrJob.STATUS_PROCESSING
        job.started_at = now
        job.attempts += 1
    await db.flush()
    return jobs


async def mark_done(db: AsyncSession, job: OcrJob, *, result: dict, page_count: int) -> None:
    job.status = OcrJob.STATUS_DONE
    job.result = result
    job.page_count = page_count
    job.error = None
    job.finished_at = datetime.now(tz=UTC)
    await db.flush()


async def mark_error(db: AsyncSession, job: OcrJob, *, error: str) -> None:
    job.status = OcrJob.STATUS_ERROR
    job.error = error[:4000]
    job.finished_at = datetime.now(tz=UTC)
    await db.flush()


async def set_callback_status(db: AsyncSession, job: OcrJob, status: str) -> None:
    job.callback_status = status[:64]
    await db.flush()
