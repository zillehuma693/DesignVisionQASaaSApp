from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class TeamMemberCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    role: str = Field(default="Engineer", max_length=64)


class TeamMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: EmailStr
    role: str
    status: str
    joined: str


class TeamListResponse(BaseModel):
    items: list[TeamMemberResponse]
    total: int
    active: int
    invited: int


class SettingsUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    workspace_name: str | None = Field(default=None, min_length=1, max_length=255)
    ai_provider: str | None = Field(default=None, max_length=64)
    notifications_enabled: bool | None = None
    email_alerts: bool | None = None
    scan_complete_notify: bool | None = None


class SettingsResponse(BaseModel):
    full_name: str
    email: str
    workspace_name: str
    ai_provider: str
    notifications_enabled: bool
    email_alerts: bool
    scan_complete_notify: bool
    api_key_hint: str | None
