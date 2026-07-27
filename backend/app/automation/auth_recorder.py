import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from urllib.parse import urlparse

from fastapi import HTTPException, status
from playwright.async_api import Browser, BrowserContext, Error as PlaywrightError, Page, Playwright, async_playwright

from app.automation.navigation import friendly_navigation_error, goto_with_retries
from app.automation.playwright_thread import PlaywrightThread
from app.core.config import settings
from app.core.crypto import encrypt_text
from app.core.logging import get_logger
from app.models.auth_profile import AuthProfile

logger = get_logger(__name__)


@dataclass
class AuthRecordingSession:
    id: uuid.UUID
    user_id: uuid.UUID
    url: str
    worker: PlaywrightThread
    playwright: Playwright
    browser: Browser
    context: BrowserContext
    page: Page
    status: str = "open"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class AuthRecorder:
    def __init__(self) -> None:
        self._sessions: dict[uuid.UUID, AuthRecordingSession] = {}

    async def start(self, user_id: uuid.UUID, url: str) -> AuthRecordingSession:
        worker = PlaywrightThread()
        try:
            playwright, browser, context, page = await worker.run(self._launch(url))
        except PlaywrightError as exc:
            worker.stop()
            logger.warning("Auth recording browser failed for %s: %s", url, exc)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=friendly_navigation_error(url, exc)
                if "net::" in str(exc) or "ERR_" in str(exc)
                else "Couldn't open a browser window. Check the URL and try again.",
            ) from exc
        except Exception:
            worker.stop()
            logger.exception("Unexpected error starting auth recording for %s", url)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Couldn't open a browser window. Check the URL and try again.",
            ) from None

        session = AuthRecordingSession(
            id=uuid.uuid4(),
            user_id=user_id,
            url=url,
            worker=worker,
            playwright=playwright,
            browser=browser,
            context=context,
            page=page,
        )
        self._sessions[session.id] = session
        return session

    async def _launch(self, url: str) -> tuple[Playwright, Browser, BrowserContext, Page]:
        """Open a headed browser; navigation is best-effort so flaky DNS doesn't block login recording."""
        playwright = await async_playwright().start()
        try:
            browser = await playwright.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()
            try:
                await goto_with_retries(page, url, timeout_ms=settings.scan_timeout_ms, attempts=3)
            except PlaywrightError as exc:
                # Keep the window open — user can still reach the site manually (VPN/DNS recovery).
                logger.warning(
                    "Initial navigation to %s failed (%s); leaving browser open for manual login",
                    url,
                    exc,
                )
                try:
                    await page.goto("about:blank")
                except Exception:
                    pass
        except Exception:
            await playwright.stop()
            raise
        return playwright, browser, context, page

    def get(self, session_id: uuid.UUID, user_id: uuid.UUID) -> AuthRecordingSession:
        session = self._sessions.get(session_id)
        if not session or session.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Auth session not found")
        self._expire_if_stale(session)
        if session.id not in self._sessions:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Auth session not found")
        return session

    def _expire_if_stale(self, session: AuthRecordingSession) -> None:
        if session.status != "open":
            return
        age = (datetime.now(UTC) - session.created_at).total_seconds()
        if age > settings.auth_session_ttl_seconds:
            session.status = "expired"
            self._sessions.pop(session.id, None)

    async def complete(self, session_id: uuid.UUID, user_id: uuid.UUID) -> AuthProfile:
        session = self.get(session_id, user_id)
        if session.status != "open":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Session is {session.status}, not open")

        try:
            state = await session.worker.run(session.context.storage_state())
        except Exception as exc:
            await self._teardown(session)
            self._sessions.pop(session_id, None)
            logger.warning("Failed to capture auth storage state for %s: %s", session_id, exc)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Couldn't save the login session. Keep the browser open until you click Save.",
            ) from exc

        await self._teardown(session)

        domain = urlparse(session.url).netloc
        profile = AuthProfile(
            user_id=user_id,
            url=session.url,
            domain=domain,
            storage_state_encrypted=encrypt_text(json.dumps(state)),
        )
        await profile.insert()
        session.status = "completed"
        self._sessions.pop(session_id, None)
        return profile

    async def cancel(self, session_id: uuid.UUID, user_id: uuid.UUID) -> None:
        session = self.get(session_id, user_id)
        if session.status == "open":
            await self._teardown(session)
        session.status = "cancelled"
        self._sessions.pop(session_id, None)

    async def _teardown(self, session: AuthRecordingSession) -> None:
        async def _close() -> None:
            try:
                await session.browser.close()
            except Exception:
                logger.warning("Error closing auth recording browser for session %s", session.id, exc_info=True)
            try:
                await session.playwright.stop()
            except Exception:
                logger.warning("Error stopping playwright for session %s", session.id, exc_info=True)

        try:
            if session.worker.is_running:
                await session.worker.run(_close())
        except Exception:
            logger.warning("Error tearing down auth session %s", session.id, exc_info=True)
        finally:
            session.worker.stop()


auth_recorder = AuthRecorder()
