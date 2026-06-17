import uuid
from datetime import datetime, timezone
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.base import CRUDBase
from app.models.alert import Alert, IncidentAlert
from app.schemas.alert import AlertCreate


class CRUDAlert(CRUDBase[Alert]):
    async def get_by_organization(
        self,
        db: AsyncSession,
        organization_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Alert]:
        result = await db.execute(
            select(Alert)
            .where(Alert.organization_id == organization_id)
            .order_by(Alert.timestamp.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_incident(
        self, db: AsyncSession, incident_id: uuid.UUID
    ) -> list[Alert]:
        result = await db.execute(
            select(Alert)
            .join(IncidentAlert, IncidentAlert.alert_id == Alert.id)
            .where(IncidentAlert.incident_id == incident_id)
        )
        return list(result.scalars().all())

    async def get_unacknowledged(
        self, db: AsyncSession, organization_id: uuid.UUID
    ) -> list[Alert]:
        result = await db.execute(
            select(Alert).where(
                and_(
                    Alert.organization_id == organization_id,
                    Alert.is_acknowledged == False,  # noqa: E712
                )
            )
        )
        return list(result.scalars().all())

    async def create(self, db: AsyncSession, *, obj_in: AlertCreate) -> Alert:
        db_obj = Alert(
            organization_id=obj_in.organization_id,
            rule_id=obj_in.rule_id,
            rule_level=obj_in.rule_level,
            rule_description=obj_in.rule_description,
            rule_groups=obj_in.rule_groups,
            agent_id=obj_in.agent_id,
            agent_name=obj_in.agent_name,
            endpoint_id=obj_in.endpoint_id,
            raw_data=obj_in.raw_data,
            timestamp=obj_in.timestamp,
            is_simulated=obj_in.is_simulated,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def acknowledge(
        self, db: AsyncSession, *, alert: Alert, user_id: uuid.UUID
    ) -> Alert:
        alert.is_acknowledged = True
        alert.acknowledged_by = user_id
        alert.acknowledged_at = datetime.now(timezone.utc)
        db.add(alert)
        await db.commit()
        await db.refresh(alert)
        return alert

    async def link_to_incident(
        self,
        db: AsyncSession,
        alert_id: uuid.UUID,
        incident_id: uuid.UUID,
        linked_by: uuid.UUID | None = None,
    ) -> IncidentAlert:
        link = IncidentAlert(
            alert_id=alert_id,
            incident_id=incident_id,
            linked_by=linked_by,
            linked_at=datetime.now(timezone.utc),
        )
        db.add(link)
        await db.commit()
        return link

    async def get_link(
        self,
        db: AsyncSession,
        alert_id: uuid.UUID,
        incident_id: uuid.UUID,
    ) -> IncidentAlert | None:
        result = await db.execute(
            select(IncidentAlert).where(
                and_(
                    IncidentAlert.alert_id == alert_id,
                    IncidentAlert.incident_id == incident_id,
                )
            )
        )
        return result.scalar_one_or_none()


alert = CRUDAlert(Alert)
