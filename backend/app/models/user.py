from datetime import UTC, datetime
from uuid import UUID, uuid4

from beanie import Document, Indexed
from pydantic import EmailStr, Field
from pymongo import ASCENDING, IndexModel

from app.core.enums import MemberStatus, TeamRole


class User(Document):
    id: UUID = Field(default_factory=uuid4)
    email: Indexed(EmailStr, unique=True)
    full_name: str
    hashed_password: str
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "users"


class RefreshToken(Document):
    id: UUID = Field(default_factory=uuid4)
    token_id: Indexed(str, unique=True)
    user_id: UUID
    family_id: UUID = Field(default_factory=uuid4)
    family_ttl_days: int = 7
    expires_at: datetime
    revoked: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "refresh_tokens"
        indexes = [
            IndexModel([("user_id", ASCENDING)]),
            IndexModel([("family_id", ASCENDING)]),
        ]


class RevokedAccessToken(Document):
    """Blacklist for access tokens invalidated before their natural expiry
    (e.g. explicit logout). Mongo TTL index auto-drops rows once the token
    would have expired anyway, so this collection never grows unbounded."""

    id: UUID = Field(default_factory=uuid4)
    jti: Indexed(str, unique=True)
    expires_at: datetime

    class Settings:
        name = "revoked_access_tokens"
        indexes = [IndexModel([("expires_at", ASCENDING)], expireAfterSeconds=0)]


class UserSettings(Document):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    workspace_name: str = "My Workspace"
    ai_provider: str = "none"
    notifications_enabled: bool = True
    email_alerts: bool = True
    scan_complete_notify: bool = True
    api_key_hint: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "user_settings"
        indexes = [IndexModel([("user_id", ASCENDING)], unique=True)]


class TeamMember(Document):
    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    name: str
    email: str
    role: str = TeamRole.ENGINEER.value
    status: str = MemberStatus.INVITED.value
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "team_members"
        indexes = [
            IndexModel([("owner_id", ASCENDING)]),
            IndexModel([("owner_id", ASCENDING), ("email", ASCENDING)], unique=True),
        ]
