import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


class EmailService:
    """Thin Resend wrapper, matching the raw-httpx convention already used
    by services/ai/provider.py rather than pulling in the Resend SDK.

    When resend_api_key is unset (default/dev), sends are logged instead of
    attempted — mirrors the existing FallbackAIProvider pattern of degrading
    gracefully rather than crashing when an integration isn't configured."""

    async def _send(self, to_email: str, subject: str, html: str) -> None:
        if not settings.resend_api_key:
            logger.info("Resend not configured — email suppressed. To: %s | Subject: %s", to_email, subject)
            return

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                RESEND_API_URL,
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                json={
                    "from": settings.resend_from_email,
                    "to": [to_email],
                    "subject": subject,
                    "html": html,
                },
            )
            if response.status_code >= 400:
                logger.error("Resend send failed (%s): %s", response.status_code, response.text)

    async def send_password_reset_email(self, to_email: str, reset_link: str) -> None:
        await self._send(
            to_email,
            "Reset your VisionQA password",
            f'<p>Click the link below to reset your password. This link expires in 1 hour.</p>'
            f'<p><a href="{reset_link}">{reset_link}</a></p>'
            f"<p>If you didn't request this, you can safely ignore this email.</p>",
        )

    async def send_verification_email(self, to_email: str, verify_link: str) -> None:
        await self._send(
            to_email,
            "Verify your VisionQA email address",
            f'<p>Click the link below to verify your email address. This link expires in 24 hours.</p>'
            f'<p><a href="{verify_link}">{verify_link}</a></p>',
        )


email_service = EmailService()
