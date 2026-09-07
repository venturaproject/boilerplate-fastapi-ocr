from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.cqrs import command_handler, query_handler
from app.repositories import document as repo

from .commands import DeleteDocument
from .queries import GetDocument, GetDocumentStats, ListDocuments


@command_handler(DeleteDocument)
async def handle_delete(session: AsyncSession, cmd: DeleteDocument) -> bool:
    doc = await repo.get_document(session, cmd.id)
    if doc is None:
        return False
    await repo.delete_document(session, doc)
    return True


@query_handler(ListDocuments)
async def handle_list(session: AsyncSession, q: ListDocuments):
    return await repo.list_documents(
        session,
        page=q.page,
        per_page=q.per_page,
        search=q.search,
        mode=q.mode,
        doc_type=q.doc_type,
        status=q.status,
    )


@query_handler(GetDocument)
async def handle_get(session: AsyncSession, q: GetDocument):
    return await repo.get_document(session, q.id)


@query_handler(GetDocumentStats)
async def handle_stats(session: AsyncSession, q: GetDocumentStats):
    return await repo.stats(session)
