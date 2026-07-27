from datetime import UTC, datetime
from uuid import UUID, uuid4

from beanie import Document
from pydantic import Field
from pymongo import ASCENDING, IndexModel


class AuthProfile(Document):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    url: str
    domain: str
    storage_state_encrypted: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "auth_profiles"
        indexes = [IndexModel([("user_id", ASCENDING)])]
