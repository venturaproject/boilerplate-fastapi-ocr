from __future__ import annotations

import hashlib
import json
import logging
from http.cookies import SimpleCookie
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.database import AsyncSessionLocal
from app.idempotency.models import IdempotencyKey
from app.services.jwt import jwt_service

logger = logging.getLogger("app.idempotency")

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
PATH_PREFIX = "/api/"


class IdempotencyMiddleware:
    """Middleware ASGI: respeta la cabecera ``Idempotency-Key`` en métodos de
    escritura bajo ``/api/``. Reintentos con misma key + mismo cuerpo devuelven la
    respuesta almacenada; cuerpo distinto -> 422; en curso -> 409."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        key = headers.get("idempotency-key")
        method = scope["method"]
        path = scope["path"]

        if not key or method not in UNSAFE_METHODS or not path.startswith(PATH_PREFIX):
            return await self.app(scope, receive, send)

        body, replay_receive = await _buffer_body(receive)
        principal = _principal(scope, headers)
        request_hash = hashlib.sha256(body).hexdigest()

        record_id, created, stored = await _reserve(key, principal, method, path, request_hash)

        if not created:
            if stored["request_hash"] != request_hash:
                return await _send_json(send, 422, {"detail": "Idempotency-Key reutilizada con otro cuerpo."})
            if stored["response_status"] == 0:
                return await _send_json(send, 409, {"detail": "Ya hay una petición idéntica en curso."})
            return await _send_json(send, stored["response_status"], stored["response_body"])

        captured: dict[str, Any] = {"status": 0, "body": b""}

        async def capture_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                captured["status"] = message["status"]
            elif message["type"] == "http.response.body":
                captured["body"] += message.get("body", b"")
            await send(message)

        try:
            await self.app(scope, replay_receive, capture_send)
        finally:
            await _persist(record_id, captured["status"], captured["body"])


async def _buffer_body(receive: Receive) -> tuple[bytes, Receive]:
    chunks: list[Message] = []
    body = b""
    while True:
        message = await receive()
        chunks.append(message)
        if message["type"] == "http.request":
            body += message.get("body", b"")
            if not message.get("more_body", False):
                break
        elif message["type"] == "http.disconnect":
            break

    async def replay() -> Message:
        if chunks:
            return chunks.pop(0)
        return {"type": "http.request", "body": b"", "more_body": False}

    return body, replay


def _principal(scope: Scope, headers: dict[str, str]) -> str:
    cookie_header = headers.get("cookie", "")
    if cookie_header:
        jar: SimpleCookie = SimpleCookie()
        jar.load(cookie_header)
        token = jar["access_token"].value if "access_token" in jar else None
        if token:
            payload = jwt_service.validate_access_token(token)
            if payload and payload.get("sub"):
                return f"user:{payload['sub']}"

    auth = headers.get("authorization", "")
    if auth.startswith("Bearer "):
        digest = hashlib.sha256(auth[len("Bearer ") :].encode()).hexdigest()[:16]
        return f"client:{digest}"

    client = scope.get("client")
    return f"anon:{client[0] if client else 'unknown'}"


async def _reserve(
    key: str, principal: str, method: str, path: str, request_hash: str
) -> tuple[int, bool, dict[str, Any]]:
    async with AsyncSessionLocal() as session, session.begin():
        inserted_id = (
            await session.execute(
                pg_insert(IdempotencyKey)
                .values(
                    key=key,
                    principal=principal,
                    method=method,
                    path=path,
                    request_hash=request_hash,
                )
                .on_conflict_do_nothing(index_elements=["key", "principal"])
                .returning(IdempotencyKey.id)
            )
        ).scalar_one_or_none()
        row = (
            await session.execute(
                select(IdempotencyKey).where(IdempotencyKey.key == key, IdempotencyKey.principal == principal)
            )
        ).scalar_one()
        return (
            row.id,
            inserted_id is not None,
            {
                "request_hash": row.request_hash,
                "response_status": row.response_status,
                "response_body": row.response_body,
            },
        )


async def _persist(record_id: int, status: int, body: bytes) -> None:
    async with AsyncSessionLocal() as session, session.begin():
        if status == 0 or status >= 500:
            await session.execute(
                delete(IdempotencyKey).where(IdempotencyKey.id == record_id, IdempotencyKey.response_status == 0)
            )
            return
        try:
            parsed = json.loads(body) if body else None
        except ValueError:
            parsed = None
        row = await session.get(IdempotencyKey, record_id)
        if row is not None and row.response_status == 0:
            row.response_status = status
            row.response_body = parsed


async def _send_json(send: Send, status: int, data: Any) -> None:
    payload = json.dumps(data).encode() if data is not None else b""
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(payload)).encode()),
                (b"idempotent-replay", b"true"),
            ],
        }
    )
    await send({"type": "http.response.body", "body": payload})
