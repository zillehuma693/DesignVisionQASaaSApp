from datetime import UTC, datetime, timedelta

from beanie.operators import In

from app.core.enums import ScanStatus
from app.models.bug import Bug
from app.models.scan import Scan
from app.models.user import User
from app.schemas.dashboard import (
    DashboardResponse,
    DashboardStats,
    RecentScanItem,
    ScanFrequencyPoint,
    TrendPoint,
)
from app.services.scan_service import scan_service


class DashboardService:
    async def get_dashboard(self, user: User) -> DashboardResponse:
        all_scans = await Scan.find(Scan.user_id == user.id).to_list()
        completed = [s for s in all_scans if s.status == ScanStatus.COMPLETED.value]

        total_scans = len(all_scans)
        scan_ids = [s.id for s in all_scans]
        all_bugs = await Bug.find(In(Bug.scan_id, scan_ids)).to_list() if scan_ids else []
        total_bugs = len(all_bugs)
        avg_health_int = int(sum(s.health_score or 0 for s in completed) / len(completed)) if completed else 0

        stats = DashboardStats(
            total_scans=total_scans,
            total_bugs=total_bugs,
            avg_health=avg_health_int,
            hours_saved=max(1, total_scans * 2),
        )

        return DashboardResponse(
            stats=stats,
            bug_trends=await self._bug_trends(user, all_bugs),
            scan_frequency=await self._scan_frequency(user, all_scans),
            recent_scans=[RecentScanItem(**item) for item in await scan_service.get_recent_for_dashboard(user)],
        )

    async def _bug_trends(self, user: User, bugs: list[Bug]) -> list[TrendPoint]:
        points = []
        for i in range(6):
            day = datetime.now(UTC) - timedelta(days=(5 - i) * 4)
            day_end = day + timedelta(days=1)
            day_bugs = [b for b in bugs if day <= b.created_at.replace(tzinfo=UTC) < day_end]
            counts: dict[str, int] = {}
            for b in day_bugs:
                counts[b.severity] = counts.get(b.severity, 0) + 1
            points.append(TrendPoint(
                date=day.strftime("%b %d"),
                critical=counts.get("critical", 0),
                high=counts.get("high", 0),
                medium=counts.get("medium", 0),
                low=counts.get("low", 0),
            ))
        return points

    async def _scan_frequency(self, user: User, scans: list[Scan]) -> list[ScanFrequencyPoint]:
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        points = []
        for i, label in enumerate(days):
            day_start = datetime.now(UTC) - timedelta(days=6 - i)
            day_end = day_start + timedelta(days=1)
            day_start = day_start.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_end.replace(hour=0, minute=0, second=0, microsecond=0)
            count = sum(
                1 for s in scans
                if day_start <= s.created_at.replace(tzinfo=UTC) < day_end
            )
            points.append(ScanFrequencyPoint(day=label, scans=count))
        return points


dashboard_service = DashboardService()
