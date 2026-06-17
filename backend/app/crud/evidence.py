import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.evidence import Evidence
from app.schemas.evidence import EvidenceCreate, EvidenceUpdate


class CRUDEvidence(CRUDBase[Evidence]):
    async def get_by_incident(self, db: AsyncSession, incident_id: uuid.UUID) -> list[Evidence]:
        result = await db.execute(
            select(Evidence)
            .where(Evidence.incident_id == incident_id)
            .order_by(Evidence.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_key_evidence(self, db: AsyncSession, incident_id: uuid.UUID) -> list[Evidence]:
        result = await db.execute(
            select(Evidence).where(
                Evidence.incident_id == incident_id,
                Evidence.is_key_evidence == True,  # noqa: E712
            )
        )
        return list(result.scalars().all())

    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: EvidenceCreate,
        incident_id: uuid.UUID,
        collected_by: uuid.UUID,
    ) -> Evidence:
        db_obj = Evidence(
            incident_id=incident_id,
            collected_by=collected_by,
            type=obj_in.type,
            title=obj_in.title,
            description=obj_in.description,
            content=obj_in.content,
            structured_data=obj_in.structured_data,
            source_alert_id=obj_in.source_alert_id,
            source_endpoint_id=obj_in.source_endpoint_id,
            is_key_evidence=obj_in.is_key_evidence,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self, db: AsyncSession, *, db_obj: Evidence, obj_in: EvidenceUpdate
    ) -> Evidence:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj


evidence = CRUDEvidence(Evidence)
