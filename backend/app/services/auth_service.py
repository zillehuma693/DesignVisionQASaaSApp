import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import HTTPException, status

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.email_token import EmailToken
from app.models.user import RefreshToken, RevokedAccessToken, User, UserSettings
from app.schemas.auth import UserCreate, UserLogin
from app.services.email_service import email_service

logger = get_logger(__name__)


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    refresh_expires_at: datetime
    csrf_token: str
    user: User


class AuthService:
    async def register(self, payload: UserCreate) -> TokenPair:
        existing = await User.find_one(User.email == payload.email.lower())
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists",
            )

        user = User(
            email=payload.email.lower(),
            full_name=payload.full_name.strip(),
            hashed_password=hash_password(payload.password),
        )
        await user.insert()
        await UserSettings(
            user_id=user.id,
            workspace_name=f"{user.full_name.split()[0]}'s Workspace",
        ).insert()

        try:
            await self.send_verification_email(user)
        except Exception:
            logger.exception("Failed to send verification email to %s", user.email)

        return await self._issue_tokens(user)

    async def login(self, payload: UserLogin) -> TokenPair:
        user = await User.find_one(User.email == payload.email.lower())
        if not user or not verify_password(payload.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated",
            )
        ttl_days = settings.remember_me_expire_days if payload.remember_me else settings.refresh_token_expire_days
        return await self._issue_tokens(user, ttl_days=ttl_days)

    async def refresh(self, refresh_token: str) -> TokenPair:
        try:
            claims = decode_token(refresh_token)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

        if claims.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

        token_id = claims.get("jti")
        user_id = claims.get("sub")
        if not token_id or not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

        stored = await RefreshToken.find_one(RefreshToken.token_id == token_id)
        if not stored or str(stored.user_id) != user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token invalid")

        if stored.revoked:
            # A revoked token being presented again means it was either already
            # rotated away, or logged out — reusing it is a signal of possible
            # token theft, so the whole session family is killed, not just
            # this one token.
            await self._revoke_family(stored.family_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token reuse detected — all sessions revoked",
            )

        expires_at = stored.expires_at if stored.expires_at.tzinfo else stored.expires_at.replace(tzinfo=UTC)
        if expires_at < datetime.now(UTC):
            stored.revoked = True
            await stored.save()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")

        user = await User.get(stored.user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        stored.revoked = True
        await stored.save()
        return await self._issue_tokens(user, family_id=stored.family_id, ttl_days=stored.family_ttl_days)

    async def logout(self, refresh_token: str) -> None:
        try:
            claims = decode_token(refresh_token)
        except ValueError:
            return

        token_id = claims.get("jti")
        if not token_id:
            return

        stored = await RefreshToken.find_one(RefreshToken.token_id == token_id)
        if stored:
            stored.revoked = True
            await stored.save()

    async def change_password(self, user: User, current_password: str, new_password: str) -> None:
        if not verify_password(current_password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect")
        user.hashed_password = hash_password(new_password)
        user.updated_at = datetime.now(UTC)
        await user.save()
        await self._revoke_all_for_user(user.id)

    async def forgot_password(self, email: str) -> None:
        user = await User.find_one(User.email == email.lower())
        if not user:
            # Deliberately silent — a differing response here would let an
            # attacker enumerate registered email addresses.
            return

        raw_token = secrets.token_urlsafe(32)
        await EmailToken(
            user_id=user.id,
            token_hash=_hash_token(raw_token),
            purpose="reset",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        ).insert()
        reset_link = f"{settings.frontend_url}/reset-password?token={raw_token}"
        await email_service.send_password_reset_email(user.email, reset_link)

    async def reset_password(self, raw_token: str, new_password: str) -> None:
        record = await self._consume_email_token(raw_token, purpose="reset")
        user = await User.get(record.user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset link")

        user.hashed_password = hash_password(new_password)
        user.updated_at = datetime.now(UTC)
        await user.save()
        await self._revoke_all_for_user(user.id)

    async def send_verification_email(self, user: User) -> None:
        raw_token = secrets.token_urlsafe(32)
        await EmailToken(
            user_id=user.id,
            token_hash=_hash_token(raw_token),
            purpose="verify",
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        ).insert()
        verify_link = f"{settings.frontend_url}/verify-email?token={raw_token}"
        await email_service.send_verification_email(user.email, verify_link)

    async def verify_email(self, raw_token: str) -> None:
        record = await self._consume_email_token(raw_token, purpose="verify")
        user = await User.get(record.user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification link")

        user.is_verified = True
        await user.save()

    async def revoke_access_token(self, jti: str, expires_at: datetime) -> None:
        if await RevokedAccessToken.find_one(RevokedAccessToken.jti == jti):
            return
        await RevokedAccessToken(jti=jti, expires_at=expires_at).insert()

    async def get_user_by_id(self, user_id: UUID) -> User:
        user = await User.get(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    async def _consume_email_token(self, raw_token: str, *, purpose: str) -> EmailToken:
        record = await EmailToken.find_one(
            EmailToken.token_hash == _hash_token(raw_token),
            EmailToken.purpose == purpose,
            EmailToken.used_at == None,  # noqa: E711
        )
        if not record:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired link")

        expires_at = record.expires_at if record.expires_at.tzinfo else record.expires_at.replace(tzinfo=UTC)
        if expires_at < datetime.now(UTC):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired link")

        record.used_at = datetime.now(UTC)
        await record.save()
        return record

    async def _revoke_all_for_user(self, user_id: UUID) -> None:
        tokens = await RefreshToken.find(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked == False,  # noqa: E712
        ).to_list()
        for token in tokens:
            token.revoked = True
            await token.save()

    async def _revoke_family(self, family_id: UUID) -> None:
        tokens = await RefreshToken.find(
            RefreshToken.family_id == family_id,
            RefreshToken.revoked == False,  # noqa: E712
        ).to_list()
        for token in tokens:
            token.revoked = True
            await token.save()

    async def _issue_tokens(
        self, user: User, *, family_id: UUID | None = None, ttl_days: int | None = None
    ) -> TokenPair:
        ttl_days = ttl_days or settings.refresh_token_expire_days
        family_id = family_id or uuid4()

        access_token = create_access_token(str(user.id), {"email": user.email})
        refresh_token, token_id = create_refresh_token(str(user.id))
        expires_at = datetime.now(UTC) + timedelta(days=ttl_days)

        await RefreshToken(
            token_id=token_id,
            user_id=user.id,
            family_id=family_id,
            family_ttl_days=ttl_days,
            expires_at=expires_at,
        ).insert()

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            refresh_expires_at=expires_at,
            csrf_token=secrets.token_urlsafe(32),
            user=user,
        )


auth_service = AuthService()
