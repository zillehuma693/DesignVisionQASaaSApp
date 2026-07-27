from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AuthSessionCreate(BaseModel):
    url: str = Field(min_length=1, max_length=2048)


class AuthSessionResponse(BaseModel):
    id: UUID
    url: str
    status: str


class AuthProfileResponse(BaseModel):
    id: UUID
    url: str
    domain: str
    created_at: datetime
