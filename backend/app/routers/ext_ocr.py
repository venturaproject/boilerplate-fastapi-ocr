import uuid

from fastapi import APIRouter, Depends, Form, Response, UploadFile
from fastapi import File as FileParam
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import ExtClientContext, require_ocr
from app.exceptions import NotFoundException, ValidationException
from app.models.ocr_job import OcrJob
from app.repositories import client_usage as usage_repo
from app.repositories import ocr_job as ocr_repo
from app.schemas.ocr import (
    ClassifyOut,
    OcrBatchResponse,
    OcrBatchStatus,
    OcrJobListResponse,
    OcrJobOut,
    OcrJobSummary,
    OcrResult,
    OcrStats,
    OcrUsageOut,
)
from app.services.ocr.jobs import (
    FormattedResult,
    classify_document,
    content_length_guard,
    create_batch_jobs,
    create_ocr_job,
    run_sync_ocr,
)

router = APIRouter(prefix="/api/ext/ocr", tags=["external-ocr"])

_sync_size_guard = Depends(content_length_guard(settings.ocr_sync_max_bytes))
_job_size_guard = Depends(content_length_guard(settings.ocr_max_upload_bytes))


@router.post("", dependencies=[_sync_size_guard])
async def ext_ocr_sync(
    file: UploadFile = FileParam(...),
    lang: str | None = Form(default=None),
    format: str = "json",
    ctx: ExtClientContext = require_ocr("ocr:write"),
) -> OcrResult:
    """Synchronous OCR. `?format=json` (default) · `text` · `hocr` · `alto` · `pdf`."""
    out = await run_sync_ocr(file, lang, fmt=format, api_client_id=ctx.client.id)
    if isinstance(out, FormattedResult):
        return Response(content=out.body, media_type=out.media_type)  # type: ignore[return-value]
    return out


@router.post("/classify", dependencies=[_sync_size_guard])
async def ext_ocr_classify(
    file: UploadFile = FileParam(...),
    lang: str | None = Form(default=None),
    ctx: ExtClientContext = require_ocr("ocr:write"),
) -> ClassifyOut:
    """OCR + document-type classification (invoice / cv / payslip / …)."""
    return await classify_document(file, lang, api_client_id=ctx.client.id)


@router.post("/jobs", status_code=202, dependencies=[_job_size_guard])
async def ext_ocr_create_job(
    response: Response,
    file: UploadFile = FileParam(...),
    lang: str | None = Form(default=None),
    callback_url: str | None = Form(default=None),
    ctx: ExtClientContext = require_ocr("ocr:write"),
    db: AsyncSession = Depends(get_db),
) -> OcrJobOut:
    """Async OCR: queue a job, poll `GET /jobs/{id}` or receive a `callback_url` POST."""
    job = await create_ocr_job(
        db,
        file,
        lang=lang,
        callback_url=callback_url,
        api_client_id=ctx.client.id,
    )
    response.headers["Location"] = f"{router.prefix}/jobs/{job.id}"
    return OcrJobOut.model_validate(job)


@router.post("/jobs:batch", status_code=202, dependencies=[_job_size_guard])
async def ext_ocr_create_batch(
    files: list[UploadFile] = FileParam(...),
    lang: str | None = Form(default=None),
    callback_url: str | None = Form(default=None),
    ctx: ExtClientContext = require_ocr("ocr:write"),
    db: AsyncSession = Depends(get_db),
) -> OcrBatchResponse:
    """Queue several files (or one .zip) as one batch. Poll `GET /batches/{batch_id}`."""
    batch_id, jobs = await create_batch_jobs(
        db, files, lang=lang, callback_url=callback_url, api_client_id=ctx.client.id
    )
    return OcrBatchResponse(
        batch_id=batch_id,
        count=len(jobs),
        jobs=[OcrJobSummary.model_validate(j) for j in jobs],
    )


@router.get("/batches/{batch_id}")
async def ext_ocr_batch_status(
    batch_id: uuid.UUID,
    ctx: ExtClientContext = require_ocr("ocr:read"),
    db: AsyncSession = Depends(get_db),
) -> OcrBatchStatus:
    items, total = await ocr_repo.list_jobs(db, api_client_id=ctx.client.id, batch_id=batch_id, per_page=1000)
    if not items:
        raise NotFoundException("Lote no encontrado")
    counts: dict[str, int] = {}
    for j in items:
        counts[j.status] = counts.get(j.status, 0) + 1
    return OcrBatchStatus(
        batch_id=batch_id,
        counts=counts,
        total=total,
        jobs=[OcrJobSummary.model_validate(j) for j in items],
    )


@router.post("/jobs/{job_id}/redeliver")
async def ext_ocr_redeliver(
    job_id: uuid.UUID,
    ctx: ExtClientContext = require_ocr("ocr:write"),
    db: AsyncSession = Depends(get_db),
) -> OcrJobOut:
    """Re-queue the webhook for a job whose callback failed / was dead-lettered."""
    job = await ocr_repo.get_job(db, job_id, api_client_id=ctx.client.id)
    if not job:
        raise NotFoundException("Job no encontrado")
    if not job.callback_url:
        raise ValidationException("El job no tiene callback_url.")
    await ocr_repo.reset_callback(db, job)
    return OcrJobOut.model_validate(job)


@router.get("/jobs")
async def ext_ocr_list_jobs(
    page: int = 1,
    per_page: int = 20,
    status: str | None = None,
    doc_type: str | None = None,
    search: str | None = None,
    callback: str | None = None,
    batch_id: uuid.UUID | None = None,
    ctx: ExtClientContext = require_ocr("ocr:read"),
    db: AsyncSession = Depends(get_db),
) -> OcrJobListResponse:
    per_page = max(1, min(per_page, 100))
    page = max(1, page)
    items, total = await ocr_repo.list_jobs(
        db,
        api_client_id=ctx.client.id,
        status=status,
        doc_type=doc_type,
        search=search,
        callback=callback,
        batch_id=batch_id,
        page=page,
        per_page=per_page,
    )
    return OcrJobListResponse(
        data=[OcrJobSummary.model_validate(j) for j in items],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/stats")
async def ext_ocr_stats(
    ctx: ExtClientContext = require_ocr("ocr:read"),
    db: AsyncSession = Depends(get_db),
) -> OcrStats:
    return await ocr_repo.stats(db, api_client_id=ctx.client.id)


@router.get("/usage")
async def ext_ocr_usage(
    ctx: ExtClientContext = require_ocr("ocr:read"),
    db: AsyncSession = Depends(get_db),
) -> OcrUsageOut:
    row = await usage_repo.get_month(db, ctx.client.id)
    pages = row.pages if row else 0
    quota = ctx.client.monthly_page_quota or settings.ocr_default_monthly_page_quota or None
    return OcrUsageOut(
        period=usage_repo.current_period(),
        pages=pages,
        requests=row.requests if row else 0,
        monthly_page_quota=quota,
        quota_remaining=max(0, quota - pages) if quota else None,
        rate_limit=ctx.client.rate_limit or settings.throttle_ocr,
    )


@router.get("/jobs/{job_id}")
async def ext_ocr_get_job(
    job_id: uuid.UUID,
    format: str = "json",
    ctx: ExtClientContext = require_ocr("ocr:read"),
    db: AsyncSession = Depends(get_db),
) -> OcrJobOut:
    job = await ocr_repo.get_job(db, job_id, api_client_id=ctx.client.id)
    if not job:
        raise NotFoundException("Job no encontrado")
    if format != "json":
        return _job_formatted(job, format)  # type: ignore[return-value]
    return OcrJobOut.model_validate(job)


def _job_formatted(job: OcrJob, fmt: str) -> Response:
    from app.services.ocr import formats
    from app.services.ocr.loader import load_pages
    from app.services.ocr.storage import read_file

    if fmt not in formats.FORMATS or fmt == "json":
        raise ValidationException(f"format inválido: {fmt}. Admitidos: text, hocr, alto, pdf.")
    if job.status != "done" or not job.result:
        raise ValidationException("El job aún no tiene resultado.")
    result = OcrResult.model_validate(job.result)

    pages = None
    if fmt == "pdf":
        try:
            data = read_file(job.storage_path)
            pages = load_pages(data, job.content_type, filename=job.original_filename)
        except Exception as exc:  # original purged by retention, or storage error
            raise ValidationException("No se puede generar el PDF: el archivo original ya no está disponible.") from exc

    body, media_type = formats.render(result, fmt, pages)
    return Response(content=body, media_type=media_type)
