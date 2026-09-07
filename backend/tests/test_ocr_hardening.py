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
