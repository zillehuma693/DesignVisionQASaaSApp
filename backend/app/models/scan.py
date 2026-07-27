from datetime import UTC, datetime
from uuid import UUID, uuid4

from beanie import Document
from pydantic import Field
from pymongo import ASCENDING, IndexModel

from app.core.enums import ScanStatus


class Scan(Document):
    id: UUID = Field(default_factory=uuid4)
    project_id: UUID | None = None
    user_id: UUID
    url: str
    status: str = ScanStatus.PENDING.value
    branch: str | None = None
    auth_profile_id: UUID | None = None
    browser: str = "chromium"
    viewport: str = "desktop"
    health_score: int | None = None
    pages_discovered: int = 0
    nodes_discovered: int = 0
    edges_discovered: int = 0
    safe_mode: bool = True
    fill_forms: bool = False
    bugs_count: int = 0
    duration_seconds: int | None = None
    ai_summary: str | None = None
    error_message: str | None = None
    progress: int = 0
    current_phase: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "scans"
        indexes = [
            IndexModel([("user_id", ASCENDING)]),
            IndexModel([("project_id", ASCENDING)]),
        ]


class ScanLog(Document):
    id: UUID = Field(default_factory=uuid4)
    scan_id: UUID
    level: str
    message: str
    source: str = "system"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "scan_logs"
        indexes = [IndexModel([("scan_id", ASCENDING)])]


class Screenshot(Document):
    id: UUID = Field(default_factory=uuid4)
    scan_id: UUID
    node_id: UUID | None = None
    file_path: str
    page_url: str
    viewport: str = "desktop"
    label: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "screenshots"
        indexes = [IndexModel([("scan_id", ASCENDING)])]


class ScanNode(Document):
    id: UUID = Field(default_factory=uuid4)
    scan_id: UUID
    url: str
    label: str
    parent_node_id: UUID | None = None
    discovered_via: dict | None = None
    dom_signature: str = ""
    lcp_ms: int | None = None
    cls: float | None = None
    ttfb_ms: int | None = None
    load_time_ms: int | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "scan_nodes"
        indexes = [IndexModel([("scan_id", ASCENDING)])]
