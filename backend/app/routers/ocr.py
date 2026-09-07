import uuid

from fastapi import APIRouter, Depends, Form, Response, UploadFile
from fastapi import File as FileParam
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user, require_permission
from app.exceptions import NotFoundException
from app.models.user import User
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
from app.services.ocr.engine import is_ready, warmed_langs
from app.services.ocr.jobs import (
    classify_document,
    content_length_guard,
    create_ocr_job,
    run_sync_ocr,
)

router = APIRouter(prefix="/api/v1/ocr", tags=["ocr"])

_ocr_limit, _ocr_per = settings.throttle(settings.throttle_ocr)
_ocr_rl = Depends(rate_limit("v1_ocr", _ocr_limit, _ocr_per))
_sync_size_guard = Depends(content_length_guard(settings.ocr_sync_max_bytes))
_job_size_guard = Depends(content_length_guard(settings.ocr_max_upload_bytes))


@router.get("/ready")
async def ocr_ready() -> Response:
    """Unauthenticated readiness probe — 200 once a model is loaded, else 503."""
    body = {"ready": is_ready(), "engine": settings.ocr_engine, "warmed_langs": warmed_langs()}
    return JSONResponse(body, status_code=200 if body["ready"] else 503)


@router.post("/scan", dependencies=[_ocr_rl, _sync_size_guard])
async def ocr_scan(
    file: UploadFile = FileParam(...),
    lang: str | None = Form(default=None),
    user: User = require_permission("ocr.use"),
) -> OcrResult:
    """Synchronous OCR playground for the dashboard."""
    return await run_sync_ocr(file, lang, created_by_user_id=user.id)


@router.post("/classify", dependencies=[_ocr_rl, _sync_size_guard])
async def ocr_classify(
    file: UploadFile = FileParam(...),
    lang: str | None = Form(default=None),
    user: User = require_permission("ocr.use"),
) -> ClassifyOut:
    """OCR + document-type classification for the dashboard."""
    return await classify_document(file, lang, created_by_user_id=user.id)


@router.post(
    "/jobs",
    status_code=202,
    dependencies=[require_permission("ocr.use"), _ocr_rl, _job_size_guard],
)
async def ocr_create_job(
    response: Response,
    file: UploadFile = FileParam(...),
    lang: str | None = Form(default=None),
    callback_url: str | None = Form(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OcrJobOut:
    job = await create_ocr_job(
        db,
        file,
        lang=lang,
        callback_url=callback_url,
        created_by_user_id=user.id,
    )
    response.headers["Location"] = f"{router.prefix}/jobs/{job.id}"
    return OcrJobOut.model_validate(job)


@router.get("/jobs", dependencies=[require_permission("ocr.jobs.view"), _ocr_rl])
async def ocr_list_jobs(
    page: int = 1,
    per_page: int = 20,
    status: str | None = None,
    doc_type: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> OcrJobListResponse:
    per_page = max(1, min(per_page, 100))
    page = max(1, page)
    items, total = await ocr_repo.list_jobs(
        db, status=status, doc_type=doc_type, page=page, per_page=per_page
    )
    return OcrJobListResponse(
        data=[OcrJobSummary.model_validate(j) for j in items],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/stats", dependencies=[require_permission("ocr.jobs.view"), _ocr_rl])
async def ocr_stats(db: AsyncSession = Depends(get_db)) -> OcrStats:
    return await ocr_repo.stats(db)


@router.get("/jobs/{job_id}", dependencies=[require_permission("ocr.jobs.view"), _ocr_rl])
async def ocr_get_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> OcrJobOut:
    job = await ocr_repo.get_job(db, job_id)
    if not job:
        raise NotFoundException("Job no encontrado")
    return OcrJobOut.model_validate(job)
