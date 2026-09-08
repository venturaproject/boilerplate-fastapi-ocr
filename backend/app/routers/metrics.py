from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import func, select

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.ocr_job import OcrJob
from app.observability.metrics import ocr_queue_depth

router = APIRouter(tags=["metrics"])

_STATUSES = ("pending", "processing", "done", "error")


async def _sample_queue_depth() -> None:
    try:
        async with AsyncSessionLocal() as db:
            rows = (await db.execute(select(OcrJob.status, func.count()).group_by(OcrJob.status))).all()
        counts: dict[str, int] = {str(status): int(n) for status, n in rows}
        for status in _STATUSES:
            ocr_queue_depth.labels(status=status).set(counts.get(status, 0))
    except Exception:  # metrics must never 500
        pass


@router.get("/metrics")
async def metrics(request: Request) -> Response:
    if settings.metrics_token:
        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {settings.metrics_token}":
            raise HTTPException(status_code=401, detail="metrics token requerido")

    await _sample_queue_depth()
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
