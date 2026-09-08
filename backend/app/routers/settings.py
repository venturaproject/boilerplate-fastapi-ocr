from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.repositories.user import get_or_create_settings

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


class NotificationSettingsRequest(BaseModel):
    notifications_all: bool | None = None
    notifications_email: bool | None = None
    notifications_push: bool | None = None


class AppearanceSettingsRequest(BaseModel):
    theme: str | None = None
    language: str | None = None
    timezone: str | None = None


@router.patch("/notifications")
async def update_notification_settings(
    body: NotificationSettingsRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    user_settings = await get_or_create_settings(db, user)
    if body.notifications_all is not None:
        user_settings.notifications_all = body.notifications_all
    if body.notifications_email is not None:
        user_settings.notifications_email = body.notifications_email
    if body.notifications_push is not None:
        user_settings.notifications_push = body.notifications_push
    await db.flush()
    return {
        "notifications_all": user_settings.notifications_all,
        "notifications_email": user_settings.notifications_email,
        "notifications_push": user_settings.notifications_push,
    }


@router.patch("/appearance")
async def update_appearance_settings(
    body: AppearanceSettingsRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str | None]:
    user_settings = await get_or_create_settings(db, user)
    if body.theme is not None:
        user_settings.theme = body.theme
    if body.language is not None:
        user_settings.language = body.language
    if body.timezone is not None:
        user_settings.timezone = body.timezone
    await db.flush()
    return {
        "theme": user_settings.theme,
        "language": user_settings.language,
        "timezone": user_settings.timezone,
    }
