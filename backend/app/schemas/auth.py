import uuid

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    login: str
    password: str


class UserSettingsOut(BaseModel):
    theme: str = "light"
    language: str = "es"
    timezone: str = "Europe/Madrid"
    notifications_all: bool = True
    notifications_email: bool = True
    notifications_push: bool = False

    model_config = {"from_attributes": True}


class AuthUserOut(BaseModel):
    id: uuid.UUID
    name: str
    username: str | None = None
    email: str
    role: str
    roles: list[str]
    permissions: list[str]
    avatar: str | None = None
    status: str
    settings: UserSettingsOut | None = None

    model_config = {"from_attributes": True}


class UpdateProfileRequest(BaseModel):
    name: str | None = None
    username: str | None = None
    email: EmailStr | None = None
