"""Run Playwright on an event loop that can spawn subprocesses.

On Windows, ``uvicorn --reload`` (and ``--workers > 1``) force the server onto
``SelectorEventLoop``, which raises ``NotImplementedError`` from
``asyncio.create_subprocess_exec``. Playwright needs that API to start its
driver, so we run Playwright work on a dedicated thread with
``ProactorEventLoop`` (or the platform default elsewhere).
"""

from __future__ import annotations

import asyncio
import sys
import threading
from collections.abc import Coroutine
from typing import Any, TypeVar

T = TypeVar("T")


class PlaywrightThread:
    """Long-lived thread owning a subprocess-capable asyncio event loop."""

    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._run, name="playwright-loop", daemon=True)
        self._thread.start()
        if not self._ready.wait(timeout=30):
            raise RuntimeError("Playwright event loop thread failed to start")

    def _run(self) -> None:
        if sys.platform == "win32":
            loop: asyncio.AbstractEventLoop = asyncio.ProactorEventLoop()
        else:
            loop = asyncio.new_event_loop()
        self._loop = loop
        asyncio.set_event_loop(loop)
        self._ready.set()
        loop.run_forever()
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()

    @property
    def is_running(self) -> bool:
        return self._loop is not None and self._loop.is_running()

    async def run(self, coro: Coroutine[Any, Any, T]) -> T:
        if not self.is_running or self._loop is None:
            raise RuntimeError("Playwright event loop is not running")
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return await asyncio.wrap_future(future)

    def stop(self) -> None:
        loop = self._loop
        if loop is None or not loop.is_running():
            return
        loop.call_soon_threadsafe(loop.stop)
        self._thread.join(timeout=30)


async def run_on_playwright_loop(coro: Coroutine[Any, Any, T]) -> T:
    """Run a one-shot Playwright coroutine, then tear down the helper thread."""
    worker = PlaywrightThread()
    try:
        return await worker.run(coro)
    finally:
        worker.stop()
