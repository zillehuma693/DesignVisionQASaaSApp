import uuid

from fastapi import HTTPException, status

from app.core.enums import MemberStatus
from app.models.user import TeamMember, User, UserSettings
from app.schemas.team import SettingsResponse, SettingsUpdate, TeamMemberCreate, TeamMemberResponse


class TeamService:
    async def list_members(self, user: User) -> tuple[list[TeamMemberResponse], int, int]:
        members = await TeamMember.find(TeamMember.owner_id == user.id).sort("created_at").to_list()
        active = sum(1 for m in members if m.status == MemberStatus.ACTIVE.value)
        invited = sum(1 for m in members if m.status == MemberStatus.INVITED.value)
        items = [
            TeamMemberResponse(
                id=m.id,
                name=m.name,
                email=m.email,
                role=m.role,
                status=m.status,
                joined=m.created_at.strftime("%b %Y") if m.status == MemberStatus.ACTIVE.value else "—",
            )
            for m in members
        ]
        return items, active, invited

    async def invite_member(self, user: User, payload: TeamMemberCreate) -> TeamMemberResponse:
        existing = await TeamMember.find_one(
            TeamMember.owner_id == user.id,
            TeamMember.email == payload.email.lower(),
        )
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Member already invited")

        member = TeamMember(
            owner_id=user.id,
            name=payload.name.strip(),
            email=payload.email.lower(),
            role=payload.role,
            status=MemberStatus.INVITED.value,
        )
        await member.insert()
        return TeamMemberResponse(
            id=member.id,
            name=member.name,
            email=member.email,
            role=member.role,
            status=member.status,
            joined="—",
        )

    async def remove_member(self, user: User, member_id: uuid.UUID) -> None:
        member = await TeamMember.find_one(TeamMember.id == member_id, TeamMember.owner_id == user.id)
        if not member:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
        await member.delete()


class SettingsService:
    async def _get_or_create(self, user: User) -> UserSettings:
        settings_doc = await UserSettings.find_one(UserSettings.user_id == user.id)
        if not settings_doc:
            settings_doc = UserSettings(
                user_id=user.id,
                workspace_name=f"{user.full_name.split()[0]}'s Workspace",
            )
            await settings_doc.insert()
        return settings_doc

    async def get_settings(self, user: User) -> SettingsResponse:
        s = await self._get_or_create(user)
        return SettingsResponse(
            full_name=user.full_name,
            email=user.email,
            workspace_name=s.workspace_name,
            ai_provider=s.ai_provider,
            notifications_enabled=s.notifications_enabled,
            email_alerts=s.email_alerts,
            scan_complete_notify=s.scan_complete_notify,
            api_key_hint=s.api_key_hint,
        )

    async def update_settings(self, user: User, payload: SettingsUpdate) -> SettingsResponse:
        from datetime import UTC, datetime

        s = await self._get_or_create(user)
        if payload.full_name is not None:
            user.full_name = payload.full_name.strip()
            user.updated_at = datetime.now(UTC)
            await user.save()
        if payload.workspace_name is not None:
            s.workspace_name = payload.workspace_name.strip()
        if payload.ai_provider is not None:
            s.ai_provider = payload.ai_provider
        if payload.notifications_enabled is not None:
            s.notifications_enabled = payload.notifications_enabled
        if payload.email_alerts is not None:
            s.email_alerts = payload.email_alerts
        if payload.scan_complete_notify is not None:
            s.scan_complete_notify = payload.scan_complete_notify
        s.updated_at = datetime.now(UTC)
        await s.save()
        return await self.get_settings(user)


team_service = TeamService()
settings_service = SettingsService()
