import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.document import Document
from app.models.ocr_job import OcrJob
from app.schemas.document import DocumentStats


def _excerpt(text: str | None) -> str | None:
    if not text:
        return None
    limit = settings.document_text_excerpt_chars
    if limit <= 0:
        return None
    return text[:limit]


async def record_document(
    db: AsyncSession,
    *,
    mode: str,
    status: str = Document.STATUS_DONE,
    api_client_id: uuid.UUID | None = None,
    created_by_user_id: uuid.UUID | None = None,
    ocr_job_id: uuid.UUID | None = None,
    original_filename: str | None = None,
    content_type: str | None = None,
    size_bytes: int = 0,
    lang: str = "es",
    page_count: int | None = None,
    processing_ms: int | None = None,
    doc_type: str | None = None,
    doc_type_confidence: float | None = None,
    text: str | None = None,
    char_count: int | None = None,
    error: str | None = None,
) -> Document:
    doc = Document(
        mode=mode,
        status=status,
        api_client_id=api_client_id,
        created_by_user_id=created_by_user_id,
        ocr_job_id=ocr_job_id,
        original_filename=(original_filename or None) and original_filename[:512],
        content_type=content_type,
        size_bytes=size_bytes,
        lang=lang,
        page_count=page_count,
        processing_ms=processing_ms,
        doc_type=doc_type,
        doc_type_confidence=doc_type_confidence,
        char_count=char_count if char_count is not None else (len(text) if text else None),
        text_excerpt=_excerpt(text),
        error=error[:4000] if error else None,
    )
    db.add(doc)
    await db.flush()
    return doc


async def get_document(
    db: AsyncSession,
    document_id: uuid.UUID,
    *,
    api_client_id: uuid.UUID | None = None,
) -> Document | None:
    stmt = select(Document).where(Document.id == document_id)
    if api_client_id is not None:
        stmt = stmt.where(Document.api_client_id == api_client_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_documents(
    db: AsyncSession,
    *,
    api_client_id: uuid.UUID | None = None,
    mode: str | None = None,
    doc_type: str | None = None,
    status: str | None = None,
    search: str | None = None,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[Document], int]:
    filters = []
    if api_client_id is not None:
        filters.append(Document.api_client_id == api_client_id)
    if mode is not None:
        filters.append(Document.mode == mode)
    if doc_type is not None:
        filters.append(Document.doc_type == doc_type)
    if status is not None:
        filters.append(Document.status == status)
    if search:
        filters.append(Document.original_filename.ilike(f"%{search}%"))

    total = (
        await db.execute(select(func.count()).select_from(Document).where(*filters))
    ).scalar_one()

    result = await db.execute(
        select(Document)
        .where(*filters)
        .order_by(Document.created_at.desc())
        .limit(per_page)
        .offset((page - 1) * per_page)
    )
    return list(result.scalars().all()), int(total)


async def delete_document(db: AsyncSession, doc: Document) -> None:
    await db.delete(doc)
    await db.flush()


async def sync_from_job(db: AsyncSession, job: OcrJob) -> None:
    """Mirror a finished `OcrJob` onto its linked `Document` row (async flow)."""
    result = await db.execute(select(Document).where(Document.ocr_job_id == job.id))
    doc = result.scalar_one_or_none()
    if doc is None:
        return

    doc.status = job.status
    doc.page_count = job.page_count
    doc.processing_ms = job.processing_ms
    doc.doc_type = job.doc_type
    doc.error = job.error[:4000] if job.error else None

    payload = job.result or {}
    text = payload.get("text") if isinstance(payload, dict) else None
    if text:
        doc.char_count = len(text)
        doc.text_excerpt = _excerpt(text)
    classification = payload.get("classification") if isinstance(payload, dict) else None
    if isinstance(classification, dict) and classification.get("doc_type"):
        doc.doc_type_confidence = classification.get("confidence")
    await db.flush()


async def stats(db: AsyncSession, *, api_client_id: uuid.UUID | None = None) -> DocumentStats:
    base_filters = []
    if api_client_id is not None:
        base_filters.append(Document.api_client_id == api_client_id)

    total = (
        await db.execute(select(func.count()).select_from(Document).where(*base_filters))
    ).scalar_one()

    cutoff_24h = datetime.now(tz=UTC) - timedelta(hours=24)
    last_24h = (
        await db.execute(
            select(func.count())
            .select_from(Document)
            .where(*base_filters, Document.created_at >= cutoff_24h)
        )
    ).scalar_one()

    by_mode = {
        m: int(n)
        for m, n in (
            await db.execute(
                select(Document.mode, func.count()).where(*base_filters).group_by(Document.mode)
            )
        ).all()
    }
    by_status = {
        s: int(n)
        for s, n in (
            await db.execute(
                select(Document.status, func.count()).where(*base_filters).group_by(Document.status)
            )
        ).all()
    }
    by_doc_type = {
        dt: int(n)
        for dt, n in (
            await db.execute(
                select(Document.doc_type, func.count())
                .where(*base_filters, Document.doc_type.isnot(None))
                .group_by(Document.doc_type)
            )
        ).all()
    }

    done_filter = [*base_filters, Document.processing_ms.isnot(None)]
    avg_ms = (
        await db.execute(select(func.avg(Document.processing_ms)).where(*done_filter))
    ).scalar_one_or_none()
    p95_ms = (
        await db.execute(
            select(
                func.percentile_cont(0.95).within_group(Document.processing_ms.asc())
            ).where(*done_filter)
        )
    ).scalar_one_or_none()

    return DocumentStats(
        total=int(total),
        last_24h=int(last_24h),
        by_mode=by_mode,
        by_status=by_status,
        by_doc_type=by_doc_type,
        processing_ms_avg=round(float(avg_ms), 1) if avg_ms is not None else None,
        processing_ms_p95=round(float(p95_ms), 1) if p95_ms is not None else None,
    )


async def purge_expired_documents(
    db: AsyncSession, *, retention_days: int, limit: int = 500
) -> int:
    """Delete document rows older than the retention window (0 disables)."""
    if retention_days <= 0:
        return 0
    cutoff = datetime.now(tz=UTC) - timedelta(days=retention_days)
    result = await db.execute(
        select(Document.id).where(Document.created_at < cutoff).limit(limit)
    )
    ids = [row[0] for row in result.all()]
    if ids:
        await db.execute(delete(Document).where(Document.id.in_(ids)))
        await db.flush()
    return len(ids)
