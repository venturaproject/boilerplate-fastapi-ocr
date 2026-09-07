from __future__ import annotations

import hashlib
import math
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, Request
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
        return "client:" + hashlib.sha256(auth[len("Bearer "):].encode()).hexdigest()[:16]

    client = request.client
    return f"ip:{client.host if client else 'unknown'}"


def rate_limit(scope: str, limit: int, per_seconds: int):
    """Devuelve una dependencia FastAPI que aplica un límite de ventana fija
    (``limit`` peticiones cada ``per_seconds``) por ``scope`` + identidad."""

    window = timedelta(seconds=per_seconds)

    async def dependency(request: Request) -> None:
        now = datetime.now(tz=UTC)
        cutoff = now - window
        key = f"{scope}:{_ident(request)}"

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

        if count > limit:
            retry_after = max(1, math.ceil((window_start + window - now).total_seconds()))
            raise HTTPException(
                status_code=429,
                detail="Demasiadas peticiones. Inténtalo más tarde.",
                headers={"Retry-After": str(retry_after)},
            )

    return dependency
