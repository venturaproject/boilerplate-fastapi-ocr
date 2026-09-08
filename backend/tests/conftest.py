from __future__ import annotations

import hashlib
import secrets
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

import app.main
from app.database import AsyncSessionLocal
from app.main import app
from app.middleware.csrf import generate_csrf_token
from app.models.api_client import ApiClient, ApiClientToken

_TABLES = (
    "documents",
    "ocr_jobs",
    "client_usage",
    "audit_events",
    "outbox_messages",
    "inbox_messages",
    "idempotency_keys",
    "rate_limit_counters",
)


async def _issue_token(name: str, scopes: list[str]) -> str:
    raw = "tok_" + secrets.token_hex(8)
    async with AsyncSessionLocal() as s, s.begin():
        client_row = ApiClient(
            name=name,
            client_id="cli_" + secrets.token_hex(6),
            secret_hash="x",
            scopes=scopes,
        )
        s.add(client_row)
        await s.flush()
        s.add(
            ApiClientToken(
                client_id=client_row.id,
                scopes=scopes,
                access_token_hash=hashlib.sha256(raw.encode()).hexdigest(),
                refresh_token_hash=secrets.token_hex(16),
                access_expires_at=datetime.now(tz=UTC) + timedelta(hours=1),
                refresh_expires_at=datetime.now(tz=UTC) + timedelta(days=1),
            )
        )
    return raw


async def _truncate() -> None:
    async with AsyncSessionLocal() as s, s.begin():
        await s.execute(text("TRUNCATE " + ", ".join(_TABLES)))
        await s.execute(text("UPDATE users SET failed_login_attempts = 0, locked_until = NULL"))


@pytest.fixture(autouse=True)
async def _clean() -> AsyncIterator[None]:
    await _truncate()
    yield
    await _truncate()


@pytest.fixture(autouse=True)
def _fake_ocr_engine(tmp_path) -> Iterator[None]:
    """Never load the real PaddleOCR model, and keep uploads out of the real media dir."""
    from app.config import settings
    from app.services.ocr import cache as ocr_cache
    from app.services.ocr import engine as ocr_engine

    prev = {
        "ocr_engine": settings.ocr_engine,
        "media_dir": settings.media_dir,
        "ocr_callback_allow_private": settings.ocr_callback_allow_private,
    }
    settings.ocr_engine = "fake"
    settings.media_dir = str(tmp_path / "media")
    settings.ocr_callback_allow_private = True  # tests post to non-resolvable hosts
    ocr_engine.get_engine.cache_clear()
    ocr_cache.clear()
    yield
    for k, v in prev.items():
        setattr(settings, k, v)
    ocr_engine.get_engine.cache_clear()
    ocr_cache.clear()


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as s:
        yield s
        await s.rollback()


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"X-CSRFToken": generate_csrf_token()},
    ) as c:
        yield c


@pytest.fixture
async def admin_client(client: AsyncClient) -> AsyncIterator[AsyncClient]:
    """`client` logged in as the seeded admin (cookie-JWT set on the client)."""
    from app.config import settings

    r = await client.post(
        "/api/v1/auth/login",
        json={"login": settings.admin_email, "password": settings.admin_password},
    )
    assert r.status_code == 200, r.text
    yield client


@pytest.fixture
async def ocr_token() -> AsyncIterator[str]:
    raw = await _issue_token("test-ocr", ["ocr:write", "ocr:read"])
    yield raw
    async with AsyncSessionLocal() as s, s.begin():
        await s.execute(text("DELETE FROM api_clients WHERE name = 'test-ocr'"))


@pytest.fixture
async def ocr_token_readonly() -> AsyncIterator[str]:
    raw = await _issue_token("test-ocr-ro", ["ocr:read"])
    yield raw
    async with AsyncSessionLocal() as s, s.begin():
        await s.execute(text("DELETE FROM api_clients WHERE name = 'test-ocr-ro'"))
