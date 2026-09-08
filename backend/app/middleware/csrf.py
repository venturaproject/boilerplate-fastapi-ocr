import secrets

from itsdangerous import BadSignature, TimestampSigner
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import settings

_signer = TimestampSigner(settings.secret_key)

MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
SKIP_PREFIXES = ("/api/ext/", "/api/v1/csrf")


def generate_csrf_token() -> str:
    raw = secrets.token_hex(32)
    return _signer.sign(raw).decode()


def validate_csrf_token(token: str) -> bool:
    try:
        _signer.unsign(token, max_age=86400)
        return True
    except BadSignature:
        return False


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        if request.method not in MUTATING_METHODS:
            return await call_next(request)

        if any(path.startswith(prefix) for prefix in SKIP_PREFIXES):
            return await call_next(request)

        csrf_header = request.headers.get("X-CSRFToken", "") or request.headers.get("X-CSRF-Token", "")
        if not csrf_header or not validate_csrf_token(csrf_header):
            return JSONResponse({"detail": "CSRF token inválido o ausente"}, status_code=403)

        return await call_next(request)
