import os
import uuid

import aiofiles
from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.ratelimit import rate_limit
from app.repositories import user as user_repo
from app.schemas.auth import AuthUserOut, LoginRequest, UpdateProfileRequest, UserSettingsOut
from app.services.auth import clear_auth_cookies, set_auth_cookies
from app.services.jwt import jwt_service
from app.services.password import verify_password

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_login_limit, _login_per = settings.throttle(settings.throttle_login)


def _build_auth_user_out(user: User) -> AuthUserOut:
    names = user.role_names
    avatar = None
    if user.settings and user.settings.avatar:
        avatar = user.settings.avatar
    user_settings = None
    if user.settings:
        user_settings = UserSettingsOut.model_validate(user.settings)
    return AuthUserOut(
        id=user.id,
        name=user.name,
        username=user.username,
        email=user.email,
        role=names[0] if names else "viewer",
        roles=names,
        permissions=user.permission_names,
        avatar=avatar,
        status=user.status,
        settings=user_settings,
    )


@router.post("/login", dependencies=[Depends(rate_limit("login", _login_limit, _login_per))])
async def login(
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    if not body.login or not body.password:
        raise HTTPException(status_code=400, detail="Email/usuario y contraseña son requeridos")

    user = await user_repo.get_user_by_login(db, body.login)
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    if user.status != User.STATUS_ACTIVE:
        raise HTTPException(status_code=403, detail="Tu cuenta está desactivada")

    set_auth_cookies(response, user.id, user.name, user.role_names, user.permission_names)

    return {
        "user": _build_auth_user_out(user),
        "message": "Login exitoso",
    }


@router.post("/logout")
async def logout(response: Response):
    clear_auth_cookies(response)
    return {"message": "Sesión cerrada"}


@router.post("/refresh")
async def refresh(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No hay refresh token")

    payload = jwt_service.validate_refresh_token(refresh_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token de refresco inválido")

    user_id = payload.get("sub")
    user = await user_repo.get_user_by_id(db, uuid.UUID(user_id))
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")

    if user.status != User.STATUS_ACTIVE:
        raise HTTPException(status_code=403, detail="Tu cuenta está desactivada")

    set_auth_cookies(response, user.id, user.name, user.role_names, user.permission_names)
    return {"message": "Token renovado"}


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return _build_auth_user_out(user)


@router.patch("/me")
async def update_me(
    body: UpdateProfileRequest,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    update_data: dict = {}
    if body.name is not None:
        update_data["name"] = body.name
    if body.username is not None:
        update_data["username"] = body.username
    if body.email is not None:
        from app.repositories.user import get_user_by_email
        existing = await get_user_by_email(db, body.email)
        if existing and existing.id != user.id:
            raise HTTPException(status_code=409, detail="Este email ya está en uso.")
        update_data["email"] = body.email

    updated = await user_repo.update_user(db, user, **update_data)

    # Refresh cookies with new name/permissions if changed
    set_auth_cookies(response, updated.id, updated.name, updated.role_names, updated.permission_names)
    return _build_auth_user_out(updated)


@router.post("/me/avatar")
async def upload_avatar(
    avatar: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not avatar.content_type or not avatar.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen")

    ext = os.path.splitext(avatar.filename or "")[1] or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    user_dir = os.path.join(settings.media_dir, "avatars", str(user.id))
    os.makedirs(user_dir, exist_ok=True)

    # Delete old avatar file if it exists
    if user.settings and user.settings.avatar:
        old_rel = user.settings.avatar.removeprefix("/media/")
        old_path = os.path.join(settings.media_dir, old_rel.removeprefix("media/"))
        if os.path.isfile(old_path):
            os.remove(old_path)

    file_path = os.path.join(user_dir, filename)
    content = await avatar.read()
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    avatar_url = f"/media/avatars/{user.id}/{filename}"
    updated = await user_repo.update_user_avatar(db, user, avatar_url)

    return {
        "message": "Avatar actualizado",
        "user": _build_auth_user_out(updated),
    }
