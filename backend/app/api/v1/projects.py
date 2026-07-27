from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectListResponse, ProjectResponse, ProjectUpdate
from app.services.project_service import project_service

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=ProjectListResponse)
async def list_projects(current_user: User = Depends(get_current_user)) -> ProjectListResponse:
    items = await project_service.list_projects(current_user)
    return ProjectListResponse(items=items, total=len(items))


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(payload: ProjectCreate, current_user: User = Depends(get_current_user)) -> ProjectResponse:
    return await project_service.create_project(current_user, payload)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: UUID, current_user: User = Depends(get_current_user)) -> ProjectResponse:
    return await project_service.get_project(current_user, project_id)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    payload: ProjectUpdate,
    current_user: User = Depends(get_current_user),
) -> ProjectResponse:
    return await project_service.update_project(current_user, project_id, payload)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: UUID, current_user: User = Depends(get_current_user)) -> None:
    await project_service.delete_project(current_user, project_id)
