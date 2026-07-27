import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status

from app.core.enums import ProjectStatus
from app.models.bug import Bug
from app.models.project import Project
from app.models.scan import Scan
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate


def _format_ago(dt: datetime | None) -> str | None:
    if not dt:
        return None
    delta = datetime.now(UTC) - (dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt)
    minutes = int(delta.total_seconds() / 60)
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    return f"{hours // 24}d ago"


class ProjectService:
    async def _to_response(self, project: Project) -> ProjectResponse:
        scans = await Scan.find(
            Scan.project_id == project.id,
            Scan.status == "completed",
        ).to_list()

        scan_count = len(scans)
        avg_health = int(sum(s.health_score or 0 for s in scans) / scan_count) if scans else 0
        total_bugs = sum(s.bugs_count for s in scans)
        last_scan = max((s.completed_at for s in scans if s.completed_at), default=None)

        return ProjectResponse(
            id=project.id,
            name=project.name,
            base_url=project.base_url,
            status=project.status,
            scans=scan_count,
            health=avg_health,
            bugs=total_bugs,
            last_scan=_format_ago(last_scan),
            created_at=project.created_at,
        )

    async def list_projects(self, user: User) -> list[ProjectResponse]:
        projects = await Project.find(Project.user_id == user.id).sort("-created_at").to_list()
        return [await self._to_response(p) for p in projects]

    async def get_project(self, user: User, project_id: uuid.UUID) -> ProjectResponse:
        project = await self._get_owned(user, project_id)
        return await self._to_response(project)

    async def create_project(self, user: User, payload: ProjectCreate) -> ProjectResponse:
        project = Project(
            user_id=user.id,
            name=payload.name.strip(),
            base_url=payload.base_url.strip(),
        )
        await project.insert()
        return await self._to_response(project)

    async def update_project(self, user: User, project_id: uuid.UUID, payload: ProjectUpdate) -> ProjectResponse:
        project = await self._get_owned(user, project_id)
        if payload.name is not None:
            project.name = payload.name.strip()
        if payload.base_url is not None:
            project.base_url = payload.base_url.strip()
        project.updated_at = datetime.now(UTC)
        await project.save()
        return await self._to_response(project)

    async def delete_project(self, user: User, project_id: uuid.UUID) -> None:
        project = await self._get_owned(user, project_id)
        await project.delete()

    async def _get_owned(self, user: User, project_id: uuid.UUID) -> Project:
        project = await Project.find_one(Project.id == project_id, Project.user_id == user.id)
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return project


project_service = ProjectService()
