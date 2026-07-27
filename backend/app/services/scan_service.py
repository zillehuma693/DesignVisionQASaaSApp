import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import HTTPException, status

from app.core.config import settings
from app.core.enums import ScanStatus
from app.models.auth_profile import AuthProfile
from app.models.bug import Bug
from app.models.project import Project
from app.models.scan import Scan, ScanLog, ScanNode, Screenshot
from app.models.user import User
from app.schemas.scan import (
    BugResponse,
    ScanCreate,
    ScanDetailResponse,
    ScanLogResponse,
    ScanNodeResponse,
    ScanResponse,
    ScreenshotResponse,
)


def _format_duration(seconds: int | None) -> str:
    if not seconds:
        return "—"
    m, s = divmod(seconds, 60)
    return f"{m}m {s:02d}s"


def _format_ago(dt: datetime | None) -> str:
    if not dt:
        return "—"
    now = datetime.now(UTC)
    dt_aware = dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt
    delta = now - dt_aware
    minutes = int(delta.total_seconds() / 60)
    if minutes < 1:
        return "just now"
    if minutes < 60:
        return f"{minutes} min ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    return f"{hours // 24}d ago"


class ScanService:
    def _to_response(self, scan: Scan) -> ScanResponse:
        return ScanResponse.model_validate(scan)

    def _screenshot_url(self, screenshot: Screenshot) -> str:
        filename = Path(screenshot.file_path).name
        return f"{settings.public_base_url}{settings.api_v1_prefix}/scans/screenshots/{filename}"

    def _bug_response(self, bug: Bug, screenshots_by_node: dict[uuid.UUID, Screenshot]) -> BugResponse:
        screenshot = screenshots_by_node.get(bug.node_id) if bug.node_id else None
        return BugResponse(
            **BugResponse.model_validate(bug).model_dump(exclude={"screenshot_url"}),
            screenshot_url=self._screenshot_url(screenshot) if screenshot else None,
        )

    async def list_scans(self, user: User, project_id: uuid.UUID | None = None, limit: int = 50) -> list[ScanResponse]:
        query = Scan.find(Scan.user_id == user.id)
        if project_id:
            query = Scan.find(Scan.user_id == user.id, Scan.project_id == project_id)
        scans = await query.sort("-created_at").limit(limit).to_list()
        return [self._to_response(s) for s in scans]

    async def get_scan(self, user: User, scan_id: uuid.UUID) -> ScanDetailResponse:
        scan = await self._get_owned(user, scan_id)
        bugs = await Bug.find(Bug.scan_id == scan.id).sort("created_at").to_list()
        logs = await ScanLog.find(ScanLog.scan_id == scan.id).sort("created_at").to_list()
        screenshots = await Screenshot.find(Screenshot.scan_id == scan.id).to_list()
        nodes = await ScanNode.find(ScanNode.scan_id == scan.id).sort("created_at").to_list()

        # A node can now have one screenshot per viewport (Phase 2); prefer the
        # scan's primary viewport as the representative thumbnail for bug links.
        screenshots_by_node: dict[uuid.UUID, Screenshot] = {}
        for s in screenshots:
            if not s.node_id:
                continue
            if s.node_id not in screenshots_by_node or s.viewport == scan.viewport:
                screenshots_by_node[s.node_id] = s

        return ScanDetailResponse(
            **ScanResponse.model_validate(scan).model_dump(),
            bugs=[self._bug_response(b, screenshots_by_node) for b in bugs],
            logs=[ScanLogResponse.model_validate(l) for l in logs],
            nodes=[ScanNodeResponse.model_validate(n) for n in nodes],
            screenshots=[
                ScreenshotResponse(
                    id=s.id,
                    page_url=s.page_url,
                    viewport=s.viewport,
                    label=s.label,
                    url=self._screenshot_url(s),
                    created_at=s.created_at,
                )
                for s in screenshots
            ],
        )

    async def create_scan(self, user: User, payload: ScanCreate) -> ScanResponse:
        if payload.project_id:
            project = await Project.find_one(Project.id == payload.project_id, Project.user_id == user.id)
            if not project:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

        if payload.auth_profile_id:
            profile = await AuthProfile.find_one(
                AuthProfile.id == payload.auth_profile_id, AuthProfile.user_id == user.id
            )
            if not profile:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Auth profile not found")

        scan = Scan(
            user_id=user.id,
            project_id=payload.project_id,
            url=payload.url.strip(),
            branch=payload.branch,
            browser=payload.browser,
            viewport=payload.viewport,
            auth_profile_id=payload.auth_profile_id,
            fill_forms=payload.fill_forms,
            status=ScanStatus.PENDING.value,
        )
        await scan.insert()
        return self._to_response(scan)

    async def get_recent_for_dashboard(self, user: User, limit: int = 5) -> list[dict]:
        scans = await Scan.find(
            Scan.user_id == user.id,
            Scan.status == ScanStatus.COMPLETED.value,
        ).sort("-completed_at").limit(limit).to_list()

        items = []
        for s in scans:
            score = s.health_score or 0
            status_label = "passed" if score >= 90 else "warning" if score >= 70 else "failed"
            items.append({
                "id": str(s.id),
                "url": s.url.replace("https://", "").replace("http://", ""),
                "score": score,
                "bugs": s.bugs_count,
                "status": status_label,
                "time": _format_duration(s.duration_seconds),
                "ago": _format_ago(s.completed_at),
                "branch": s.branch or "main",
            })
        return items

    async def _get_owned(self, user: User, scan_id: uuid.UUID) -> Scan:
        scan = await Scan.find_one(Scan.id == scan_id, Scan.user_id == user.id)
        if not scan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")
        return scan


class BugService:
    async def _screenshot_for(self, scan_id: uuid.UUID, node_id: uuid.UUID | None) -> Screenshot | None:
        if not node_id:
            return None
        return await Screenshot.find_one(Screenshot.scan_id == scan_id, Screenshot.node_id == node_id)

    async def list_bugs(self, user: User, scan_id: uuid.UUID) -> list[BugResponse]:
        scan = await Scan.find_one(Scan.id == scan_id, Scan.user_id == user.id)
        if not scan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")
        bugs = await Bug.find(Bug.scan_id == scan_id).sort("created_at").to_list()
        screenshots = await Screenshot.find(Screenshot.scan_id == scan_id).to_list()
        screenshots_by_node = {s.node_id: s for s in screenshots if s.node_id}
        return [scan_service._bug_response(b, screenshots_by_node) for b in bugs]

    async def get_bug(self, user: User, bug_id: uuid.UUID) -> BugResponse:
        bug = await Bug.get(bug_id)
        if not bug:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bug not found")
        scan = await Scan.find_one(Scan.id == bug.scan_id, Scan.user_id == user.id)
        if not scan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bug not found")
        screenshot = await self._screenshot_for(bug.scan_id, bug.node_id)
        return scan_service._bug_response(bug, {bug.node_id: screenshot} if screenshot else {})

    async def update_bug(self, user: User, bug_id: uuid.UUID, status_value: str) -> BugResponse:
        bug = await Bug.get(bug_id)
        if not bug:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bug not found")
        scan = await Scan.find_one(Scan.id == bug.scan_id, Scan.user_id == user.id)
        if not scan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bug not found")
        bug.status = status_value
        await bug.save()
        screenshot = await self._screenshot_for(bug.scan_id, bug.node_id)
        return scan_service._bug_response(bug, {bug.node_id: screenshot} if screenshot else {})


scan_service = ScanService()
bug_service = BugService()
