from __future__ import annotations

import io
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from PIL import Image

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.ocr_job import OcrJob
from app.ocr.processor import drain_once, purge_once
from app.services.ocr import storage

JOBS = "/api/ext/ocr/jobs"


def _png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (40, 20), "white").save(buf, format="PNG")
    return buf.getvalue()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _make_job(**overrides) -> OcrJob:
    job_id = overrides.pop("id", uuid.uuid4())
    overrides.setdefault("status", OcrJob.STATUS_PENDING)
    path = await storage.save_upload(job_id, "x.png", _png())
    async with AsyncSessionLocal() as db, db.begin():
        job = OcrJob(
            id=job_id,
            storage_path=path,
            original_filename="x.png",
            content_type="image/png",
            size_bytes=100,
            lang="es",
            **overrides,
        )
        db.add(job)
    return job


async def _get(job_id: uuid.UUID) -> OcrJob:
    async with AsyncSessionLocal() as db:
        return await db.get(OcrJob, job_id)


# ── SSRF ─────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "url",
    ["http://127.0.0.1/hook", "http://localhost/hook", "http://10.1.2.3/hook", "http://169.254.169.254/latest"],
)
async def test_callback_url_ssrf_rejected(client, ocr_token, monkeypatch, url):
    monkeypatch.setattr(settings, "ocr_callback_allow_private", False)
    r = await client.post(
        JOBS,
        files={"file": ("d.png", _png(), "image/png")},
        data={"callback_url": url},
        headers=_auth(ocr_token),
    )
    assert r.status_code == 422


async def test_callback_url_allowlist(client, ocr_token, monkeypatch):
    monkeypatch.setattr(settings, "ocr_callback_allow_private", True)
    monkeypatch.setattr(settings, "ocr_callback_allowed_hosts", "hooks.example.com")
    ok = await client.post(
        JOBS,
        files={"file": ("d.png", _png(), "image/png")},
        data={"callback_url": "https://hooks.example.com/x"},
        headers=_auth(ocr_token),
    )
    assert ok.status_code == 202
    bad = await client.post(
        JOBS,
        files={"file": ("d.png", _png(), "image/png")},
        data={"callback_url": "https://evil.example/x"},
        headers=_auth(ocr_token),
    )
    assert bad.status_code == 422


# ── Zombie reclaim ───────────────────────────────────────────────────────────


async def test_reclaims_stale_processing_job(monkeypatch):
    monkeypatch.setattr(settings, "ocr_job_stale_seconds", 0)
    job = await _make_job(
        status=OcrJob.STATUS_PROCESSING,
        started_at=datetime.now(tz=UTC) - timedelta(minutes=30),
        attempts=1,
    )
    await drain_once()
    reclaimed = await _get(job.id)
    assert reclaimed.status == OcrJob.STATUS_DONE
    assert reclaimed.result is not None


async def test_stale_job_fails_after_max_attempts(monkeypatch):
    monkeypatch.setattr(settings, "ocr_job_stale_seconds", 0)
    monkeypatch.setattr(settings, "ocr_job_max_attempts", 3)
    job = await _make_job(
        status=OcrJob.STATUS_PROCESSING,
        started_at=datetime.now(tz=UTC) - timedelta(minutes=30),
        attempts=3,
    )
    await drain_once()
    assert (await _get(job.id)).status == OcrJob.STATUS_ERROR


# ── Retention purge ──────────────────────────────────────────────────────────


async def test_purge_removes_old_finished_jobs_and_files(monkeypatch):
    monkeypatch.setattr(settings, "ocr_job_retention_days", 7)
    old = await _make_job(status=OcrJob.STATUS_DONE)
    fresh = await _make_job(status=OcrJob.STATUS_DONE)
    # backdate `old` past the retention window
    async with AsyncSessionLocal() as db, db.begin():
        row = await db.get(OcrJob, old.id)
        row.created_at = datetime.now(tz=UTC) - timedelta(days=30)

    import os

    assert os.path.exists(old.storage_path)
    purged = await purge_once()
    assert purged == 1
    assert await _get(old.id) is None
    assert await _get(fresh.id) is not None
    assert not os.path.exists(old.storage_path)


async def test_purge_keeps_unfinished_jobs(monkeypatch):
    monkeypatch.setattr(settings, "ocr_job_retention_days", 7)
    job = await _make_job(status=OcrJob.STATUS_PENDING)
    async with AsyncSessionLocal() as db, db.begin():
        row = await db.get(OcrJob, job.id)
        row.created_at = datetime.now(tz=UTC) - timedelta(days=30)
    assert await purge_once() == 0
    assert await _get(job.id) is not None


# ── Listing payload / stats / readiness ──────────────────────────────────────


async def test_list_excludes_result_detail_includes_it(client, ocr_token):
    r = await client.post(
        JOBS, files={"file": ("d.png", _png(), "image/png")}, headers=_auth(ocr_token)
    )
    job_id = r.json()["id"]
    await drain_once()

    lst = await client.get(JOBS, headers=_auth(ocr_token))
    assert lst.status_code == 200
    row = lst.json()["data"][0]
    assert "result" not in row
    assert row["processing_ms"] is not None

    detail = await client.get(f"{JOBS}/{job_id}", headers=_auth(ocr_token))
    assert detail.json()["result"]["page_count"] == 1


async def test_stats_endpoint(client, ocr_token):
    await client.post(JOBS, files={"file": ("d.png", _png(), "image/png")}, headers=_auth(ocr_token))
    await drain_once()
    r = await client.get("/api/ext/ocr/stats", headers=_auth(ocr_token))
    assert r.status_code == 200
    body = r.json()
    assert body["done"] == 1
    assert body["processing_ms_avg"] is not None


async def test_ready_endpoint(client):
    r = await client.get("/api/v1/ocr/ready")
    assert r.status_code == 200  # fake engine is always ready
    assert r.json()["ready"] is True


async def test_create_job_sets_location_header(client, ocr_token):
    r = await client.post(
        JOBS, files={"file": ("d.png", _png(), "image/png")}, headers=_auth(ocr_token)
    )
    assert r.status_code == 202
    assert r.headers["location"] == f"/api/ext/ocr/jobs/{r.json()['id']}"


# ── Loader guards ────────────────────────────────────────────────────────────


def test_pdf_page_zoom_is_clamped(monkeypatch):
    import pymupdf

    from app.services.ocr.loader import load_pages

    monkeypatch.setattr(settings, "ocr_max_image_megapixels", 1.0)
    monkeypatch.setattr(settings, "ocr_pdf_dpi", 600)  # would blow past 1 MP without clamping

    doc = pymupdf.open()
    doc.new_page(width=1000, height=1000)  # 1000pt @ 600dpi = huge
    pages = load_pages(doc.tobytes(), "application/pdf", max_pages=None)

    assert len(pages) == 1
    assert pages[0].width * pages[0].height <= 1_000_000 * 1.05


async def test_content_length_guard_rejects_large_header():
    from app.exceptions import PayloadTooLargeException
    from app.services.ocr.jobs import content_length_guard

    dep = content_length_guard(1000)

    class _Req:
        headers = {"content-length": "10000000"}

    with pytest.raises(PayloadTooLargeException):
        await dep(_Req())


def test_sort_reading_order_groups_rows():
    from app.schemas.ocr import OcrLine
    from app.services.ocr.engine import _sort_reading_order

    def line(text, x, y):
        return OcrLine(text=text, confidence=0.9, box=[[x, y], [x + 50, y], [x + 50, y + 12], [x, y + 12]])

    # given out of order: bottom-right, top-right, top-left, bottom-left
    scrambled = [line("D", 200, 100), line("B", 200, 10), line("A", 10, 12), line("C", 10, 98)]
    ordered = [ln.text for ln in _sort_reading_order(scrambled)]
    assert ordered == ["A", "B", "C", "D"]
