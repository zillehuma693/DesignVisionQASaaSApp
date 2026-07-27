from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.scan import BugResponse, BugUpdate
from app.schemas.team import SettingsResponse, SettingsUpdate, TeamListResponse, TeamMemberCreate, TeamMemberResponse
from app.services.scan_service import bug_service
from app.services.team_service import settings_service, team_service

router = APIRouter(tags=["team", "settings", "bugs"])


@router.get("/team", response_model=TeamListResponse)
async def list_team(current_user: User = Depends(get_current_user)) -> TeamListResponse:
    items, active, invited = await team_service.list_members(current_user)
    return TeamListResponse(items=items, total=len(items), active=active, invited=invited)


@router.post("/team", response_model=TeamMemberResponse, status_code=status.HTTP_201_CREATED)
async def invite_member(payload: TeamMemberCreate, current_user: User = Depends(get_current_user)) -> TeamMemberResponse:
    return await team_service.invite_member(current_user, payload)


@router.delete("/team/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(member_id: UUID, current_user: User = Depends(get_current_user)) -> None:
    await team_service.remove_member(current_user, member_id)


@router.get("/settings", response_model=SettingsResponse)
async def get_settings(current_user: User = Depends(get_current_user)) -> SettingsResponse:
    return await settings_service.get_settings(current_user)


@router.patch("/settings", response_model=SettingsResponse)
async def update_settings(payload: SettingsUpdate, current_user: User = Depends(get_current_user)) -> SettingsResponse:
    return await settings_service.update_settings(current_user, payload)


@router.get("/bugs/{bug_id}", response_model=BugResponse)
async def get_bug(bug_id: UUID, current_user: User = Depends(get_current_user)) -> BugResponse:
    return await bug_service.get_bug(current_user, bug_id)


@router.patch("/bugs/{bug_id}", response_model=BugResponse)
async def update_bug(bug_id: UUID, payload: BugUpdate, current_user: User = Depends(get_current_user)) -> BugResponse:
    if not payload.status:
        raise HTTPException(status_code=400, detail="Status is required")
    return await bug_service.update_bug(current_user, bug_id, payload.status)


@router.get("/billing/plans")
async def billing_plans() -> dict:
    return {
        "current_plan": "Pro",
        "plans": [
            {"id": "starter", "name": "Starter", "price": 49, "scans": 100},
            {"id": "pro", "name": "Pro", "price": 149, "scans": 500, "current": True},
            {"id": "enterprise", "name": "Enterprise", "price": None, "scans": "Unlimited"},
        ],
        "usage": {"scans_used": 0, "scans_limit": 500},
        "message": "Billing integration coming soon.",
    }


@router.get("/figma/status")
async def figma_status() -> dict:
    return {
        "available": False,
        "message": "Figma comparison is coming soon. Connect your Figma account to compare designs with live pages.",
    }
