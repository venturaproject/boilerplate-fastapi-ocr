import uuid

from fastapi import APIRouter, Depends, Form, UploadFile
from fastapi import File as FileParam
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_permission
from app.exceptions import NotFoundException
from app.models.user import User
from app.repositories import ocr_job as ocr_repo
from app.schemas.ocr import OcrJobListResponse, OcrJobOut, OcrResult
from app.services.ocr.jobs import create_ocr_job, run_sync_ocr

router = APIRouter(prefix="/api/v1/ocr", tags=["ocr"])


@router.post("/scan", dependencies=[require_permission("ocr.use")])
async def ocr_scan(
    file: UploadFile = FileParam(...),
    lang: str | None = Form(default=None),
) -> OcrResult:
    """Synchronous OCR playground for the dashboard."""
    return await run_sync_ocr(file, lang)


@router.post("/jobs", status_code=202, dependencies=[require_permission("ocr.use")])
async def ocr_create_job(
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
    return OcrJobOut.model_validate(job)


@router.get("/jobs", dependencies=[require_permission("ocr.jobs.view")])
async def ocr_list_jobs(
    page: int = 1,
    per_page: int = 20,
    db: AsyncSession = Depends(get_db),
) -> OcrJobListResponse:
    per_page = max(1, min(per_page, 100))
    page = max(1, page)
    items, total = await ocr_repo.list_jobs(db, page=page, per_page=per_page)
    return OcrJobListResponse(
        data=[OcrJobOut.model_validate(j) for j in items],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/jobs/{job_id}", dependencies=[require_permission("ocr.jobs.view")])
async def ocr_get_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> OcrJobOut:
    job = await ocr_repo.get_job(db, job_id)
    if not job:
        raise NotFoundException("Job no encontrado")
    return OcrJobOut.model_validate(job)
