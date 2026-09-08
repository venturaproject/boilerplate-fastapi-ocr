from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.observability.context import request_id_var
from app.observability.metrics import http_request_duration_seconds, http_requests_total

_HEADER = "X-Request-ID"
_access = logging.getLogger("app.access")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Generate/propagate an X-Request-ID and record a coarse HTTP metric."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        rid = request.headers.get(_HEADER, "").strip() or uuid.uuid4().hex
        token = request_id_var.set(rid)
        start = time.perf_counter()
        try:
            response = await call_next(request)
            elapsed = time.perf_counter() - start
            method = request.method
            path = request.url.path
            if path != "/metrics":
                http_requests_total.labels(method=method, status=str(response.status_code)).inc()
                http_request_duration_seconds.labels(method=method).observe(elapsed)
                _access.info(
                    "%s %s -> %s",
                    method,
                    path,
                    response.status_code,
                    extra={"status": response.status_code, "duration_ms": round(elapsed * 1000, 1)},
                )
            response.headers[_HEADER] = rid
            return response
        finally:
            request_id_var.reset(token)
