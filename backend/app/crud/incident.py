import uuid
from datetime import datetime, timezone
from sqlalchemy import select, text, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.base import CRUDBase
from app.models.incident import Incident, IncidentStatus, INCIDENT_TRANSITIONS
from app.schemas.incident import IncidentCreate, IncidentUpdate


class CRUDIncident(CRUDBase[Incident]):
    async def _next_incident_number(self, db: AsyncSession) -> str:
        import uuid as _uuid
        year = datetime.now(timezone.utc).year
        try:
            result = await db.execute(text("SELECT nextval('incident_number_seq')"))
            seq = result.scalar_one()
            return f"INC-{year}-{seq:04d}"
        except Exception:
            short = str(_uuid.uuid4()).replace("-", "")[:6].upper()
            return f"INC-{year}-{short}"

    async def get_by_organization(
        self,
        db: AsyncSession,
        organization_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Incident]:
        result = await db.execute(
            select(Incident)
            .where(Incident.organization_id == organization_id)
            .order_by(Incident.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_team(
        self, db: AsyncSession, team_id: uuid.UUID
    ) -> list[Incident]:
        result = await db.execute(
            select(Incident).where(Incident.team_id == team_id)
        )
        return list(result.scalars().all())

    async def get_by_assignee(
        self, db: AsyncSession, user_id: uuid.UUID
    ) -> list[Incident]:
        result = await db.execute(
            select(Incident).where(Incident.assigned_to == user_id)
        )
        return list(result.scalars().all())

    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: IncidentCreate,
        created_by: uuid.UUID,
    ) -> Incident:
        incident_number = await self._next_incident_number(db)
        db_obj = Incident(
            organization_id=obj_in.organization_id,
            incident_number=incident_number,
            title=obj_in.title,
            description=obj_in.description,
            severity=obj_in.severity,
            category=obj_in.category,
            team_id=obj_in.team_id,
            assigned_to=obj_in.assigned_to,
            detected_at=datetime.now(timezone.utc),
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self, db: AsyncSession, *, db_obj: Incident, obj_in: IncidentUpdate
    ) -> Incident:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def transition_status(
        self,
        db: AsyncSession,
        *,
        incident: Incident,
        new_status: IncidentStatus,
    ) -> Incident:
        allowed = INCIDENT_TRANSITIONS.get(incident.status, set())
        if new_status not in allowed:
            raise ValueError(
                f"Cannot transition from {incident.status} to {new_status}"
            )

        now = datetime.now(timezone.utc)
        incident.status = new_status
        if new_status == IncidentStatus.contained:
            incident.contained_at = now
        elif new_status == IncidentStatus.resolved:
            incident.resolved_at = now
        elif new_status == IncidentStatus.closed:
            incident.closed_at = now

        db.add(incident)
        await db.commit()
        await db.refresh(incident)
        return incident


incident = CRUDIncident(Incident)
