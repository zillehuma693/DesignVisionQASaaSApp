from app.models.auth_profile import AuthProfile
from app.models.bug import Bug
from app.models.email_token import EmailToken
from app.models.project import Project
from app.models.scan import Scan, ScanLog, ScanNode, Screenshot
from app.models.user import RefreshToken, RevokedAccessToken, TeamMember, User, UserSettings

ALL_DOCUMENT_MODELS = [
    User,
    RefreshToken,
    RevokedAccessToken,
    EmailToken,
    UserSettings,
    TeamMember,
    Project,
    Scan,
    ScanLog,
    Screenshot,
    ScanNode,
    Bug,
    AuthProfile,
]

__all__ = [
    "ALL_DOCUMENT_MODELS",
    "User",
    "RefreshToken",
    "RevokedAccessToken",
    "EmailToken",
    "UserSettings",
    "TeamMember",
    "Project",
    "Scan",
    "ScanLog",
    "Screenshot",
    "ScanNode",
    "Bug",
    "AuthProfile",
]
