import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class RoleSimple(BaseModel):
    id: uuid.UUID
    name: str

    model_config = {"from_attributes": True}


class UserSettingsOut(BaseModel):
    theme: str = "light"
    language: str = "es"
    timezone: str = "Europe/Madrid"
    notifications_all: bool = True
    notifications_email: bool = True
    notifications_push: bool = False

    model_config = {"from_attributes": True}


class UserOut(BaseModel):
    id: uuid.UUID
    name: str
    username: str | None = None
    email: str
    status: str
    roles: list[RoleSimple] = []
    permissions: list[str] = []
    avatar: str | None = None
    created_at: datetime
    settings: UserSettingsOut | None = None

    model_config = {"from_attributes": True}


class UserStatsOut(BaseModel):
    total: int
    activos: int
    inactivos: int
    suspendidos: int


class UserListResponse(BaseModel):
    data: list[UserOut]
    current_page: int
    last_page: int
    per_page: int
    total: int
    stats: UserStatsOut
    roles: list[RoleSimple]


class CreateUserRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    username: str | None = None
    status: str = "active"
    role_ids: list[uuid.UUID] = []


class UpdateUserRequest(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    password: str | None = None
    username: str | None = None
    status: str | None = None
    role_ids: list[uuid.UUID] | None = None
