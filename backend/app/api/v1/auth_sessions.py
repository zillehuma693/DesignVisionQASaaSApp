from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user
from app.automation.auth_recorder import auth_recorder
from app.models.user import User
from app.schemas.auth_session import AuthProfileResponse, AuthSessionCreate, AuthSessionResponse

router = APIRouter(prefix="/auth-sessions", tags=["auth-sessions"])


@router.post("", response_model=AuthSessionResponse, status_code=status.HTTP_201_CREATED)
async def start_auth_session(
    payload: AuthSessionCreate,
    current_user: User = Depends(get_current_user),
) -> AuthSessionResponse:
    session = await auth_recorder.start(current_user.id, payload.url.strip())
    return AuthSessionResponse(id=session.id, url=session.url, status=session.status)


@router.get("/{session_id}", response_model=AuthSessionResponse)
async def get_auth_session(session_id: UUID, current_user: User = Depends(get_current_user)) -> AuthSessionResponse:
    session = auth_recorder.get(session_id, current_user.id)
    return AuthSessionResponse(id=session.id, url=session.url, status=session.status)


@router.post("/{session_id}/complete", response_model=AuthProfileResponse)
async def complete_auth_session(session_id: UUID, current_user: User = Depends(get_current_user)) -> AuthProfileResponse:
    profile = await auth_recorder.complete(session_id, current_user.id)
    return AuthProfileResponse(id=profile.id, url=profile.url, domain=profile.domain, created_at=profile.created_at)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_auth_session(session_id: UUID, current_user: User = Depends(get_current_user)) -> None:
    await auth_recorder.cancel(session_id, current_user.id)
