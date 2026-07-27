from datetime import UTC, datetime
from uuid import UUID, uuid4

from beanie import Document
from pydantic import Field
from pymongo import ASCENDING, IndexModel

from app.core.enums import ProjectStatus


class Project(Document):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    name: str
    base_url: str
    status: str = ProjectStatus.PASSING.value
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "projects"
        indexes = [IndexModel([("user_id", ASCENDING)])]
