import math
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.cqrs import command_bus, query_bus
from app.database import get_db
from app.dependencies import require_permission
from app.domain.document.commands import DeleteDocument
from app.domain.document.queries import GetDocument, GetDocumentStats, ListDocuments
from app.exceptions import NotFoundException
from app.schemas.document import DocumentListResponse, DocumentOut, DocumentStats

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


@router.get("", dependencies=[require_permission("documents.view")])
async def list_documents(
    page: int = 1,
    per_page: int = 20,
    search: str | None = None,
    mode: str | None = None,
    doc_type: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> DocumentListResponse:
    per_page = max(1, min(per_page, 100))
    page = max(1, page)
    items, total = await query_bus.ask(
        db,
        ListDocuments(
            page=page,
            per_page=per_page,
            search=search,
            mode=mode,
            doc_type=doc_type,
            status=status,
        ),
    )
    last_page = max(1, math.ceil(total / per_page))
    return DocumentListResponse(
        data=[DocumentOut.model_validate(d) for d in items],
        current_page=page,
        last_page=last_page,
        per_page=per_page,
        total=total,
    )


@router.get("/stats", dependencies=[require_permission("documents.view")])
async def document_stats(db: AsyncSession = Depends(get_db)) -> DocumentStats:
    return await query_bus.ask(db, GetDocumentStats())


@router.get("/{document_id}", dependencies=[require_permission("documents.view")])
async def get_document(document_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> DocumentOut:
    doc = await query_bus.ask(db, GetDocument(id=document_id))
    if not doc:
        raise NotFoundException()
    return DocumentOut.model_validate(doc)


@router.delete(
    "/{document_id}",
    dependencies=[require_permission("documents.delete")],
    status_code=204,
)
async def delete_document(document_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> None:
    deleted = await command_bus.dispatch(db, DeleteDocument(id=document_id))
    if not deleted:
        raise NotFoundException()
