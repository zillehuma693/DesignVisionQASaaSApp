import enum


class ScanStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class BugSeverity(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class BugStatus(str, enum.Enum):
    OPEN = "open"
    FIXED = "fixed"
    IGNORED = "ignored"


class TeamRole(str, enum.Enum):
    ADMIN = "Admin"
    ENGINEER = "Engineer"
    DESIGNER = "Designer"
    VIEWER = "Viewer"


class MemberStatus(str, enum.Enum):
    ACTIVE = "active"
    INVITED = "invited"


class ProjectStatus(str, enum.Enum):
    PASSING = "passing"
    WARNING = "warning"
    FAILING = "failing"
