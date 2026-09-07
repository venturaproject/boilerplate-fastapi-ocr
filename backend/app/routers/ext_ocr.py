import uuid

from fastapi import APIRouter, Depends, Form, Response, UploadFile
from fastapi import File as FileParam
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import ExtClientContext, require_scope
from app.exceptions import NotFoundException
from app.ratelimit import rate_limit
from app.repositories import ocr_job as ocr_repo
from app.schemas.ocr import (
    ClassifyOut,
    OcrJobListResponse,
    OcrJobOut,
    OcrJobSummary,
    OcrResult,
    OcrStats,
)
from app.services.ocr.jobs import (
    classify_document,
    content_length_guard,
    create_ocr_job,
    run_sync_ocr,
)

router = APIRouter(prefix="/api/ext/ocr", tags=["external-ocr"])

_ocr_limit, _ocr_per = settings.throttle(settings.throttle_ocr)
_ocr_rl = Depends(rate_limit("ext_ocr", _ocr_limit, _ocr_per))
_sync_size_guard = Depends(content_length_guard(settings.ocr_sync_max_bytes))
_job_size_guard = Depends(content_length_guard(settings.ocr_max_upload_bytes))


@router.post("", dependencies=[_ocr_rl, _sync_size_guard])
async def ext_ocr_sync(
    file: UploadFile = FileParam(...),
    lang: str | None = Form(default=None),
    ctx: ExtClientContext = require_scope("ocr:write"),
) -> OcrResult:
    """Synchronous OCR: send a file, get the recognised text back in the response."""
    return await run_sync_ocr(file, lang)


@router.post("/classify", dependencies=[_ocr_rl, _sync_size_guard])
async def ext_ocr_classify(
    file: UploadFile = FileParam(...),
    lang: str | None = Form(default=None),
    ctx: ExtClientContext = require_scope("ocr:write"),
) -> ClassifyOut:
    """OCR + document-type classification (invoice / cv / payslip / …). Not stored."""
    return await classify_document(file, lang)


@router.post("/jobs", status_code=202, dependencies=[_ocr_rl, _job_size_guard])
async def ext_ocr_create_job(
    response: Response,
    file: UploadFile = FileParam(...),
    lang: str | None = Form(default=None),
    callback_url: str | None = Form(default=None),
    ctx: ExtClientContext = require_scope("ocr:write"),
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


@router.get("/jobs", dependencies=[_ocr_rl])
async def ext_ocr_list_jobs(
    page: int = 1,
    per_page: int = 20,
    status: str | None = None,
    doc_type: str | None = None,
    ctx: ExtClientContext = require_scope("ocr:read"),
    db: AsyncSession = Depends(get_db),
) -> OcrJobListResponse:
    per_page = max(1, min(per_page, 100))
    page = max(1, page)
    items, total = await ocr_repo.list_jobs(
        db,
        api_client_id=ctx.client.id,
        status=status,
        doc_type=doc_type,
        page=page,
        per_page=per_page,
    )
    return OcrJobListResponse(
        data=[OcrJobSummary.model_validate(j) for j in items],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/stats", dependencies=[_ocr_rl])
async def ext_ocr_stats(
    ctx: ExtClientContext = require_scope("ocr:read"),
    db: AsyncSession = Depends(get_db),
) -> OcrStats:
    return await ocr_repo.stats(db, api_client_id=ctx.client.id)


@router.get("/jobs/{job_id}", dependencies=[_ocr_rl])
async def ext_ocr_get_job(
    job_id: uuid.UUID,
    ctx: ExtClientContext = require_scope("ocr:read"),
    db: AsyncSession = Depends(get_db),
) -> OcrJobOut:
    job = await ocr_repo.get_job(db, job_id, api_client_id=ctx.client.id)
    if not job:
        raise NotFoundException("Job no encontrado")
    return OcrJobOut.model_validate(job)
