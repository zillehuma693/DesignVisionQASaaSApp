from datetime import UTC, datetime
from uuid import UUID, uuid4

from beanie import Document
from pydantic import Field
from pymongo import ASCENDING, IndexModel

from app.core.enums import BugSeverity, BugStatus


class Bug(Document):
    id: UUID = Field(default_factory=uuid4)
    scan_id: UUID
    node_id: UUID | None = None
    severity: str = BugSeverity.MEDIUM.value
    status: str = BugStatus.OPEN.value
    title: str
    component: str = "Unknown"
    description: str
    selector: str | None = None
    page_url: str | None = None
    ai_explanation: str | None = None
    fix_suggestion: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "bugs"
        indexes = [IndexModel([("scan_id", ASCENDING)])]
