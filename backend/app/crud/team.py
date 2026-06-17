import uuid

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.team import Team, TeamMember, TeamMemberRole
from app.schemas.team import TeamCreate, TeamUpdate


class CRUDTeam(CRUDBase[Team]):
    async def get_by_course(self, db: AsyncSession, course_id: uuid.UUID) -> list[Team]:
        result = await db.execute(select(Team).where(Team.course_id == course_id))
        return list(result.scalars().all())

    async def create(self, db: AsyncSession, *, obj_in: TeamCreate) -> Team:
        db_obj = Team(
            course_id=obj_in.course_id,
            name=obj_in.name,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(self, db: AsyncSession, *, db_obj: Team, obj_in: TeamUpdate) -> Team:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj


class CRUDTeamMember(CRUDBase[TeamMember]):
    async def get_by_team_and_user(
        self, db: AsyncSession, team_id: uuid.UUID, user_id: uuid.UUID
    ) -> TeamMember | None:
        result = await db.execute(
            select(TeamMember).where(
                and_(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
            )
        )
        return result.scalar_one_or_none()

    async def get_by_team(self, db: AsyncSession, team_id: uuid.UUID) -> list[TeamMember]:
        result = await db.execute(select(TeamMember).where(TeamMember.team_id == team_id))
        return list(result.scalars().all())

    async def get_by_user(self, db: AsyncSession, user_id: uuid.UUID) -> list[TeamMember]:
        result = await db.execute(select(TeamMember).where(TeamMember.user_id == user_id))
        return list(result.scalars().all())

    async def add_member(
        self,
        db: AsyncSession,
        team_id: uuid.UUID,
        user_id: uuid.UUID,
        role: TeamMemberRole = TeamMemberRole.analyst,
    ) -> TeamMember:
        db_obj = TeamMember(team_id=team_id, user_id=user_id, role=role)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update_role(
        self, db: AsyncSession, *, member: TeamMember, role: TeamMemberRole
    ) -> TeamMember:
        member.role = role
        db.add(member)
        await db.commit()
        await db.refresh(member)
        return member


team = CRUDTeam(Team)
team_member = CRUDTeamMember(TeamMember)
