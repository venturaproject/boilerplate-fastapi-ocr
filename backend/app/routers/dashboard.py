from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import require_permission
from app.models.document import Document
from app.repositories import document as document_repo
from app.repositories import ocr_job as ocr_repo
from app.schemas.dashboard import DashboardResponse, RecentDocument

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("", dependencies=[require_permission("dashboard.view")])
async def get_dashboard(db: AsyncSession = Depends(get_db)) -> DashboardResponse:
    documents = await document_repo.stats(db)
    jobs = await ocr_repo.stats(db)

    recent_rows = (
        (
            await db.execute(
                select(Document).order_by(Document.created_at.desc()).limit(settings.dashboard_recent_documents_limit)
            )
        )
        .scalars()
        .all()
    )

    recent = [
        RecentDocument(
            id=str(d.id),
            original_filename=d.original_filename,
            mode=d.mode,
            status=d.status,
            doc_type=d.doc_type,
            lang=d.lang,
            page_count=d.page_count,
            processing_ms=d.processing_ms,
            created_at=d.created_at.isoformat(),
        )
        for d in recent_rows
    ]

    return DashboardResponse(documents=documents, jobs=jobs, recent=recent)
