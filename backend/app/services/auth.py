import uuid

from fastapi import Response

from app.config import settings
from app.services.jwt import jwt_service


def set_auth_cookies(
    response: Response, user_id: uuid.UUID, name: str, roles: list[str], permissions: list[str]
) -> None:
    access_token = jwt_service.generate_access_token(user_id, name, roles, permissions)
    refresh_token, _ = jwt_service.generate_refresh_token(user_id)

    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=settings.jwt_access_ttl_seconds,
        samesite=settings.cookie_samesite,
        secure=settings.cookie_secure,
        httponly=True,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=settings.jwt_refresh_ttl_seconds,
        samesite=settings.cookie_samesite,
        secure=settings.cookie_secure,
        httponly=True,
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
