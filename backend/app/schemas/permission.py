import uuid
from datetime import datetime

from pydantic import BaseModel


class PermissionOut(BaseModel):
    id: uuid.UUID
    name: str
    guard_name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PermissionListResponse(BaseModel):
    data: list[PermissionOut]
    groups: list[str]
    current_page: int
    last_page: int
    per_page: int
    total: int
