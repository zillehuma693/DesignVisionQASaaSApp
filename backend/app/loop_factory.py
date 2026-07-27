"""Event-loop factory for uvicorn on Windows.

``uvicorn --reload`` normally forces ``SelectorEventLoop`` on Windows, which
cannot spawn subprocesses — Playwright needs that to start its driver.
Always prefer ``ProactorEventLoop`` on Windows so scans and login recording
work with or without ``--reload``.

Usage:
    uvicorn app.main:app --reload --loop app.loop_factory:event_loop_factory
"""

from __future__ import annotations

import asyncio
import sys


def event_loop_factory() -> asyncio.AbstractEventLoop:
    if sys.platform == "win32":
        return asyncio.ProactorEventLoop()
    return asyncio.new_event_loop()
