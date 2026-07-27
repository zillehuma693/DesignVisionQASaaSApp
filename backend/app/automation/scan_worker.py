"""Run a single scan in a child process (Windows --reload fallback).

When the parent uvicorn worker is stuck on SelectorEventLoop, it cannot
spawn Playwright's driver. This module is invoked as:

    python -m app.automation.scan_worker <scan_id>

and always uses a Proactor-capable loop so Playwright + Motor work together.
"""

from __future__ import annotations

import asyncio
import sys
from uuid import UUID


async def _amain(scan_id: UUID) -> None:
    from app.automation.playwright_runner import PlaywrightRunner
    from app.core.enums import ScanStatus
    from app.core.logging import setup_logging
    from app.db.mongodb import close_mongodb_connection, connect_to_mongodb
    from app.models.scan import Scan

    setup_logging()
    await connect_to_mongodb()
    try:
        scan = await Scan.get(scan_id)
        if not scan:
            return
        # Another worker (or in-process task) already claimed this scan.
        if scan.status not in {ScanStatus.PENDING.value, ScanStatus.RUNNING.value}:
            return
        if scan.status == ScanStatus.RUNNING.value and scan.progress and scan.progress > 5:
            return
        await PlaywrightRunner().run_scan(scan_id)
    finally:
        await close_mongodb_connection()


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python -m app.automation.scan_worker <scan_id>", file=sys.stderr)
        sys.exit(2)

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(_amain(UUID(sys.argv[1])))


if __name__ == "__main__":
    main()
