from __future__ import annotations

import io

from PIL import Image

from app.ocr.processor import drain_once

SYNC = "/api/ext/ocr"
CLASSIFY = "/api/ext/ocr/classify"
JOBS = "/api/ext/ocr/jobs"
PANEL = "/api/v1/documents"


def _png(size: tuple[int, int] = (48, 24)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, "white").save(buf, format="PNG")
    return buf.getvalue()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _list(session, **filters):
    from app.repositories import document as repo

    return await repo.list_documents(session, **filters)


async def test_sync_call_records_a_document(client, ocr_token, session):
    r = await client.post(SYNC, files={"file": ("factura.png", _png(), "image/png")}, headers=_auth(ocr_token))
    assert r.status_code == 200, r.text

    items, total = await _list(session, mode="sync")
    assert total == 1
    doc = items[0]
    assert doc.mode == "sync"
    assert doc.status == "done"
    assert doc.original_filename == "factura.png"
    assert doc.char_count and doc.char_count > 0
    assert doc.text_excerpt


async def test_classify_call_records_a_document(client, ocr_token, session):
    r = await client.post(CLASSIFY, files={"file": ("cv.png", _png(), "image/png")}, headers=_auth(ocr_token))
    assert r.status_code == 200, r.text

    items, total = await _list(session, mode="classify")
    assert total == 1
    assert items[0].mode == "classify"


async def test_async_job_document_tracks_the_job(client, ocr_token, session):
    r = await client.post(JOBS, files={"file": ("doc.png", _png(), "image/png")}, headers=_auth(ocr_token))
    assert r.status_code == 202, r.text

    items, _ = await _list(session, mode="async")
    assert len(items) == 1
    assert items[0].status == "pending"
    assert items[0].ocr_job_id is not None

    assert await drain_once() == 1

    session.expire_all()
    items, _ = await _list(session, mode="async")
    assert items[0].status == "done"
    assert items[0].page_count == 1
    assert items[0].text_excerpt


async def test_panel_lists_and_filters(admin_client, ocr_token):
    await admin_client.post(SYNC, files={"file": ("a.png", _png(), "image/png")}, headers=_auth(ocr_token))
    await admin_client.post(CLASSIFY, files={"file": ("b.png", _png(), "image/png")}, headers=_auth(ocr_token))

    r = await admin_client.get(PANEL)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 2

    r = await admin_client.get(PANEL, params={"mode": "classify"})
    assert r.json()["total"] == 1

    r = await admin_client.get(f"{PANEL}/stats")
    assert r.status_code == 200
    assert r.json()["total"] == 2
    assert r.json()["by_mode"].get("sync") == 1


async def test_panel_delete_and_missing(admin_client, ocr_token):
    await admin_client.post(SYNC, files={"file": ("a.png", _png(), "image/png")}, headers=_auth(ocr_token))
    doc_id = (await admin_client.get(PANEL)).json()["data"][0]["id"]

    r = await admin_client.delete(f"{PANEL}/{doc_id}")
    assert r.status_code == 204
    assert (await admin_client.get(PANEL)).json()["total"] == 0

    r = await admin_client.delete(f"{PANEL}/{doc_id}")
    assert r.status_code == 404


async def test_panel_requires_auth(client):
    assert (await client.get(PANEL)).status_code == 401
