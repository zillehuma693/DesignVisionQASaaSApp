import asyncio
import json
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import FileResponse, HTMLResponse
from sse_starlette.sse import EventSourceResponse

from app.api.deps import get_current_user
from app.automation.playwright_runner import run_scan_background
from app.core.config import settings
from app.models.user import User
from app.schemas.scan import BugResponse, ScanCreate, ScanDetailResponse, ScanListResponse, ScanResponse
from app.services.export_service import export_service
from app.services.scan_service import bug_service, scan_service

router = APIRouter(prefix="/scans", tags=["scans"])


@router.get("/screenshots/{filename}")
async def get_screenshot(filename: str) -> FileResponse:
    path = Path(settings.screenshots_path) / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Screenshot not found")
    return FileResponse(path)


@router.get("", response_model=ScanListResponse)
async def list_scans(
    project_id: UUID | None = None,
    current_user: User = Depends(get_current_user),
) -> ScanListResponse:
    items = await scan_service.list_scans(current_user, project_id)
    return ScanListResponse(items=items, total=len(items))


@router.post("", response_model=ScanResponse, status_code=status.HTTP_201_CREATED)
async def create_scan(
    payload: ScanCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
) -> ScanResponse:
    scan = await scan_service.create_scan(current_user, payload)
    background_tasks.add_task(run_scan_background, scan.id)
    return scan


@router.get("/{scan_id}", response_model=ScanDetailResponse)
async def get_scan(scan_id: UUID, current_user: User = Depends(get_current_user)) -> ScanDetailResponse:
    return await scan_service.get_scan(current_user, scan_id)


@router.get("/{scan_id}/bugs", response_model=list[BugResponse])
async def list_scan_bugs(scan_id: UUID, current_user: User = Depends(get_current_user)) -> list[BugResponse]:
    return await bug_service.list_bugs(current_user, scan_id)


@router.get("/{scan_id}/export", response_class=HTMLResponse)
async def export_scan_report(scan_id: UUID, current_user: User = Depends(get_current_user)) -> HTMLResponse:
    html = await export_service.generate_html_report(current_user, scan_id)
    return HTMLResponse(content=html)


@router.get("/{scan_id}/stream")
async def scan_progress_stream(scan_id: UUID, current_user: User = Depends(get_current_user)):
    await scan_service.get_scan(current_user, scan_id)

    async def event_generator():
        last_progress = -1
        while True:
            detail = await scan_service.get_scan(current_user, scan_id)
            if detail.progress != last_progress or detail.status in ("completed", "failed"):
                last_progress = detail.progress
                yield {
                    "event": "progress",
                    "data": json.dumps({
                        "status": detail.status,
                        "progress": detail.progress,
                        "phase": detail.current_phase,
                        "bugs_count": detail.bugs_count,
                    }),
                }
            if detail.status in ("completed", "failed"):
                break
            await asyncio.sleep(1)

    return EventSourceResponse(event_generator())
