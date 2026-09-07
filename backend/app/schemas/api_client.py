import uuid
from datetime import datetime

from pydantic import BaseModel


class ApiClientOut(BaseModel):
    id: uuid.UUID
    name: str
    client_id: str
    scopes: list[str]
    active: bool
    last_used_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CreateApiClientRequest(BaseModel):
    name: str
    scopes: list[str]


class ApiClientCreatedResponse(BaseModel):
    client: ApiClientOut
    secret: str


class ExtTokenRequest(BaseModel):
    client_id: str
    client_secret: str


class ExtRefreshRequest(BaseModel):
    refresh_token: str


class ExtTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    scopes: list[str] = []
