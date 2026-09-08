from __future__ import annotations

import hashlib
import math
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, Request, Response
from sqlalchemy import case
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import AsyncSessionLocal
from app.ratelimit.models import RateLimitCounter
from app.services.jwt import jwt_service


def _ident(request: Request) -> str:
    token = request.cookies.get("access_token")
    if token:
        payload = jwt_service.validate_access_token(token)
        if payload and payload.get("sub"):
            return f"user:{payload['sub']}"

    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        return "client:" + hashlib.sha256(auth[len("Bearer ") :].encode()).hexdigest()[:16]

    client = request.client
    return f"ip:{client.host if client else 'unknown'}"


async def enforce(
    key: str,
    limit: int,
    per_seconds: int,
    *,
    response: Response | None = None,
) -> None:
    """Fixed-window rate limit for `key`. Sets X-RateLimit-* on `response` and
    raises 429 (with Retry-After) when exceeded."""
    window = timedelta(seconds=per_seconds)
    now = datetime.now(tz=UTC)
    cutoff = now - window

    stmt = (
        pg_insert(RateLimitCounter)
        .values(key=key, window_start=now, count=1)
        .on_conflict_do_update(
            index_elements=["key"],
            set_={
                "count": case(
                    (RateLimitCounter.window_start < cutoff, 1),
                    else_=RateLimitCounter.count + 1,
                ),
                "window_start": case(
                    (RateLimitCounter.window_start < cutoff, now),
                    else_=RateLimitCounter.window_start,
                ),
            },
        )
        .returning(RateLimitCounter.count, RateLimitCounter.window_start)
    )
    async with AsyncSessionLocal() as session, session.begin():
        count, window_start = (await session.execute(stmt)).one()

    reset = window_start + window
    if response is not None:
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit - int(count)))
        response.headers["X-RateLimit-Reset"] = str(int(reset.timestamp()))

    if count > limit:
        retry_after = max(1, math.ceil((reset - now).total_seconds()))
        raise HTTPException(
            status_code=429,
            detail="Demasiadas peticiones. Inténtalo más tarde.",
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(reset.timestamp())),
            },
        )


def rate_limit(scope: str, limit: int, per_seconds: int) -> Callable[[Request, Response], Awaitable[None]]:
    """FastAPI dependency: `limit` requests per `per_seconds` per (scope, identity)."""

    async def dependency(request: Request, response: Response) -> None:
        await enforce(f"{scope}:{_ident(request)}", limit, per_seconds, response=response)

    return dependency
