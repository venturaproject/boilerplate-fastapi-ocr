import mimetypes
import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, Response

from app.config import settings
from app.services.jwt import jwt_service

AVATARS_PREFIX = "/media/avatars/"


class PrivateMediaMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if not request.url.path.startswith(AVATARS_PREFIX):
            return await call_next(request)

        token = request.cookies.get("access_token")
        if not token:
            return Response(status_code=403)

        payload = jwt_service.validate_access_token(token)
        if not payload:
            return Response(status_code=403)

        rel = request.url.path[len(AVATARS_PREFIX):]
        if ".." in rel or rel.startswith("/"):
            return Response(status_code=404)

        full_path = os.path.join(settings.media_dir, "avatars", rel)
        if not os.path.isfile(full_path):
            return Response(status_code=404)

        content_type, _ = mimetypes.guess_type(full_path)
        return FileResponse(
            full_path,
            media_type=content_type or "application/octet-stream",
            headers={"Cache-Control": "private, no-store"},
        )
