from fastapi import APIRouter, Response

from app.config import settings
from app.middleware.csrf import generate_csrf_token

router = APIRouter(tags=["csrf"])


@router.get("/api/v1/csrf/")
async def get_csrf_token(response: Response):
    token = generate_csrf_token()
    response.set_cookie(
        key="csrftoken",
        value=token,
        httponly=False,
        samesite=settings.cookie_samesite,
        secure=settings.cookie_secure,
        max_age=86400,
    )
    return {"csrfToken": token}
