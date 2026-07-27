from pydantic import BaseModel


class DashboardStats(BaseModel):
    total_scans: int
    total_bugs: int
    avg_health: int
    hours_saved: int


class TrendPoint(BaseModel):
    date: str
    critical: int
    high: int
    medium: int
    low: int


class ScanFrequencyPoint(BaseModel):
    day: str
    scans: int


class RecentScanItem(BaseModel):
    id: str
    url: str
    score: int
    bugs: int
    status: str
    time: str
    ago: str
    branch: str | None


class DashboardResponse(BaseModel):
    stats: DashboardStats
    bug_trends: list[TrendPoint]
    scan_frequency: list[ScanFrequencyPoint]
    recent_scans: list[RecentScanItem]
