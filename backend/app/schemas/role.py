import uuid
from datetime import datetime

from pydantic import BaseModel


class PermissionSimple(BaseModel):
    id: uuid.UUID
    name: str

    model_config = {"from_attributes": True}


class RoleOut(BaseModel):
    id: uuid.UUID
    name: str
    guard_name: str
    permissions: list[PermissionSimple] = []
    permissions_count: int = 0
    users_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class RoleListResponse(BaseModel):
    data: list[RoleOut]
    current_page: int
    last_page: int
    per_page: int
    total: int


class CreateRoleRequest(BaseModel):
    name: str
    guard_name: str = "api"
    permission_ids: list[uuid.UUID] = []


class UpdateRoleRequest(BaseModel):
    name: str | None = None
    permission_ids: list[uuid.UUID] | None = None
