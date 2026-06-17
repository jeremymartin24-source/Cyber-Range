import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.base import CRUDBase
from app.models.student_decision import StudentDecision, DecisionType


class CRUDStudentDecision(CRUDBase[StudentDecision]):
    async def get_by_incident(
        self, db: AsyncSession, incident_id: uuid.UUID
    ) -> list[StudentDecision]:
        result = await db.execute(
            select(StudentDecision)
            .where(StudentDecision.incident_id == incident_id)
            .order_by(StudentDecision.decided_at)
        )
        return list(result.scalars().all())

    async def get_by_user(
        self, db: AsyncSession, user_id: uuid.UUID
    ) -> list[StudentDecision]:
        result = await db.execute(
            select(StudentDecision)
            .where(StudentDecision.user_id == user_id)
            .order_by(StudentDecision.decided_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_incident_and_user(
        self, db: AsyncSession, incident_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[StudentDecision]:
        result = await db.execute(
            select(StudentDecision)
            .where(
                StudentDecision.incident_id == incident_id,
                StudentDecision.user_id == user_id,
            )
            .order_by(StudentDecision.decided_at)
        )
        return list(result.scalars().all())

    async def record(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        decision_type: DecisionType,
        decision_data: dict,
        incident_id: uuid.UUID | None = None,
        rationale: str | None = None,
    ) -> StudentDecision:
        from datetime import datetime, timezone

        db_obj = StudentDecision(
            user_id=user_id,
            incident_id=incident_id,
            decision_type=decision_type,
            decision_data=decision_data,
            rationale=rationale,
            decided_at=datetime.now(timezone.utc),
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update_score(
        self,
        db: AsyncSession,
        *,
        decision: StudentDecision,
        score: float,
        feedback: str,
    ) -> StudentDecision:
        decision.auto_score = score
        decision.auto_feedback = feedback
        db.add(decision)
        await db.commit()
        await db.refresh(decision)
        return decision


student_decision = CRUDStudentDecision(StudentDecision)
