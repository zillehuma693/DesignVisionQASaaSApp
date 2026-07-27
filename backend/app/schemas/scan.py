from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ScanCreate(BaseModel):
    url: str = Field(min_length=1, max_length=2048)
    project_id: UUID | None = None
    branch: str | None = Field(default=None, max_length=255)
    browser: str = Field(default="chromium", max_length=64)
    viewport: str = Field(default="desktop", max_length=64)
    auth_profile_id: UUID | None = None
    fill_forms: bool = False


class ScanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID | None
    url: str
    status: str
    branch: str | None
    auth_profile_id: UUID | None
    browser: str
    viewport: str
    health_score: int | None
    pages_discovered: int
    nodes_discovered: int
    edges_discovered: int
    bugs_count: int
    duration_seconds: int | None
    ai_summary: str | None
    error_message: str | None
    progress: int
    current_phase: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class ScanListResponse(BaseModel):
    items: list[ScanResponse]
    total: int


class ScanLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    level: str
    message: str
    source: str
    created_at: datetime


class ScreenshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    page_url: str
    viewport: str
    label: str | None
    url: str
    created_at: datetime


class ScanNodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    url: str
    label: str
    parent_node_id: UUID | None
    discovered_via: dict | None
    lcp_ms: int | None
    cls: float | None
    ttfb_ms: int | None
    load_time_ms: int | None
    created_at: datetime


class ScanDetailResponse(ScanResponse):
    logs: list[ScanLogResponse] = []
    screenshots: list[ScreenshotResponse] = []
    bugs: list["BugResponse"] = []
    nodes: list[ScanNodeResponse] = []


class BugResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    scan_id: UUID
    node_id: UUID | None = None
    severity: str
    status: str
    title: str
    component: str
    description: str
    selector: str | None
    page_url: str | None
    ai_explanation: str | None
    fix_suggestion: str | None
    created_at: datetime
    screenshot_url: str | None = None


class BugUpdate(BaseModel):
    status: str | None = None


class BugListResponse(BaseModel):
    items: list[BugResponse]
    total: int


ScanDetailResponse.model_rebuild()
