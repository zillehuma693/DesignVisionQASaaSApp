from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials

from app.api.deps import bearer_scheme, get_current_user
from app.core.config import settings
from app.core.security import decode_token
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    MessageResponse,
    ResetPasswordRequest,
    UserCreate,
    UserLogin,
    UserResponse,
    VerifyEmailRequest,
)
from app.services.auth_service import TokenPair, auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE_NAME = "refresh_token"
CSRF_COOKIE_NAME = "csrf_token"
REFRESH_COOKIE_PATH = f"{settings.api_v1_prefix}/auth"


def _set_session_cookies(response: Response, pair: TokenPair) -> None:
    max_age = max(0, int((pair.refresh_expires_at - datetime.now(UTC)).total_seconds()))
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        pair.refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path=REFRESH_COOKIE_PATH,
        max_age=max_age,
    )
    # Non-httpOnly by design: the frontend reads this and echoes it back as
    # an X-CSRF-Token header (double-submit pattern) on the two cookie-authed
    # endpoints below. Its value never needs to be secret from the browser,
    # only unforgeable by a cross-site attacker who can't read our cookies.
    response.set_cookie(
        CSRF_COOKIE_NAME,
        pair.csrf_token,
        httponly=False,
        secure=settings.cookie_secure,
        samesite="lax",
        path=REFRESH_COOKIE_PATH,
        max_age=max_age,
    )


def _clear_session_cookies(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)
    response.delete_cookie(CSRF_COOKIE_NAME, path=REFRESH_COOKIE_PATH)


def _to_auth_response(pair: TokenPair) -> AuthResponse:
    return AuthResponse(access_token=pair.access_token, user=UserResponse.model_validate(pair.user))


async def verify_csrf(request: Request) -> None:
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    header_token = request.headers.get("x-csrf-token")
    if not cookie_token or not header_token or cookie_token != header_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token missing or invalid")


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, response: Response) -> AuthResponse:
    pair = await auth_service.register(payload)
    _set_session_cookies(response, pair)
    return _to_auth_response(pair)


@router.post("/login", response_model=AuthResponse)
async def login(payload: UserLogin, response: Response) -> AuthResponse:
    pair = await auth_service.login(payload)
    _set_session_cookies(response, pair)
    return _to_auth_response(pair)


@router.post("/refresh", response_model=AuthResponse, dependencies=[Depends(verify_csrf)])
async def refresh(request: Request, response: Response) -> AuthResponse:
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token present")
    pair = await auth_service.refresh(refresh_token)
    _set_session_cookies(response, pair)
    return _to_auth_response(pair)


@router.post("/logout", response_model=MessageResponse, dependencies=[Depends(verify_csrf)])
async def logout(
    request: Request,
    response: Response,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> MessageResponse:
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if refresh_token:
        await auth_service.logout(refresh_token)

    # Best-effort: also kill the specific access token presented at logout
    # time, so this session dies immediately instead of lingering for up to
    # its remaining 30-minute lifetime.
    if credentials:
        try:
            claims = decode_token(credentials.credentials)
            jti, exp = claims.get("jti"), claims.get("exp")
            if jti and exp:
                await auth_service.revoke_access_token(jti, datetime.fromtimestamp(exp, tz=UTC))
        except ValueError:
            pass

    _clear_session_cookies(response)
    return MessageResponse(message="Logged out successfully")


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    payload: ChangePasswordRequest, current_user: User = Depends(get_current_user)
) -> MessageResponse:
    await auth_service.change_password(current_user, payload.current_password, payload.new_password)
    return MessageResponse(message="Password changed. You've been signed out of other devices.")


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(payload: ForgotPasswordRequest) -> MessageResponse:
    await auth_service.forgot_password(payload.email)
    return MessageResponse(message="If an account exists for that email, a reset link has been sent.")


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(payload: ResetPasswordRequest) -> MessageResponse:
    await auth_service.reset_password(payload.token, payload.new_password)
    return MessageResponse(message="Password has been reset. Please sign in.")


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(payload: VerifyEmailRequest) -> MessageResponse:
    await auth_service.verify_email(payload.token)
    return MessageResponse(message="Email verified.")


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(current_user: User = Depends(get_current_user)) -> MessageResponse:
    await auth_service.send_verification_email(current_user)
    return MessageResponse(message="Verification email sent.")
