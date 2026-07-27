"""Resilient Playwright navigation helpers."""

from __future__ import annotations

import asyncio
import re

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Page, Response

# Chromium/Playwright network failures that are often transient (flaky DNS, brief outages).
_RETRYABLE_NAV_PATTERNS = (
    "ERR_NAME_NOT_RESOLVED",
    "ERR_CONNECTION_REFUSED",
    "ERR_CONNECTION_RESET",
    "ERR_CONNECTION_CLOSED",
    "ERR_CONNECTION_TIMED_OUT",
    "ERR_NETWORK_CHANGED",
    "ERR_INTERNET_DISCONNECTED",
    "ERR_TIMED_OUT",
    "NS_ERROR_UNKNOWN_HOST",
    "Timeout",
    "timeout",
    "net::ERR_",
)


def is_retryable_navigation_error(exc: BaseException) -> bool:
    message = str(exc)
    return any(token in message for token in _RETRYABLE_NAV_PATTERNS)


def friendly_navigation_error(url: str, exc: BaseException) -> str:
    message = str(exc)
    if "ERR_NAME_NOT_RESOLVED" in message or "NS_ERROR_UNKNOWN_HOST" in message:
        host = re.sub(r"^https?://", "", url).split("/")[0] or url
        return (
            f"Could not resolve hostname for {url}. "
            f"Check that '{host}' is reachable from this machine "
            "(DNS/VPN/network), then retry the scan."
        )
    if "ERR_CONNECTION_REFUSED" in message:
        return f"Connection refused while loading {url}. Is the site up?"
    if "ERR_CONNECTION_TIMED_OUT" in message or "Timeout" in message or "timeout" in message:
        return f"Timed out loading {url}. The site may be slow or unreachable."
    if "ERR_INTERNET_DISCONNECTED" in message or "ERR_NETWORK_CHANGED" in message:
        return f"Network changed or disconnected while loading {url}. Check your connection and retry."
    return f"Failed to load {url}: {message.splitlines()[0][:300]}"


async def goto_with_retries(
    page: Page,
    url: str,
    *,
    timeout_ms: int,
    attempts: int = 3,
    wait_until: str = "domcontentloaded",
    delay_seconds: float = 1.5,
) -> Response | None:
    """Navigate with retries for flaky DNS / transient network errors."""
    last_error: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            return await page.goto(url, wait_until=wait_until, timeout=timeout_ms)
        except PlaywrightError as exc:
            last_error = exc
            if attempt >= attempts or not is_retryable_navigation_error(exc):
                raise
            await asyncio.sleep(delay_seconds * attempt)
        except Exception as exc:
            last_error = exc
            if attempt >= attempts or not is_retryable_navigation_error(exc):
                raise
            await asyncio.sleep(delay_seconds * attempt)
    assert last_error is not None
    raise last_error
