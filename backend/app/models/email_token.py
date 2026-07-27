from datetime import UTC, datetime
from uuid import UUID, uuid4

from beanie import Document, Indexed
from pydantic import Field
from pymongo import ASCENDING, IndexModel


class EmailToken(Document):
    """Single-use tokens for password reset / email verification.

    Only a SHA-256 hash of the raw token is stored, never the raw value
    itself — mirrors the existing RefreshToken pattern of never persisting
    a usable secret directly.
    """

    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    token_hash: Indexed(str, unique=True)
    purpose: str  # "reset" | "verify"
    expires_at: datetime
    used_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "email_tokens"
        indexes = [IndexModel([("user_id", ASCENDING)])]
