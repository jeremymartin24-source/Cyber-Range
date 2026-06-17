"""
Records student decisions as side effects of API actions.
Each public function is called from a route handler after the primary action succeeds.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.student_decision import student_decision as decision_crud
from app.models.student_decision import DecisionType


async def record(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    decision_type: DecisionType,
    decision_data: dict,
    incident_id: uuid.UUID | None = None,
    rationale: str | None = None,
) -> None:
    await decision_crud.record(
        db,
        user_id=user_id,
        decision_type=decision_type,
        decision_data=decision_data,
        incident_id=incident_id,
        rationale=rationale,
    )


async def triage_started(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    incident_id: uuid.UUID,
    severity: str,
    rationale: str | None = None,
) -> None:
    await record(
        db,
        user_id=user_id,
        decision_type=DecisionType.initial_triage,
        decision_data={"severity": severity},
        incident_id=incident_id,
        rationale=rationale,
    )


async def severity_changed(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    incident_id: uuid.UUID,
    old_severity: str,
    new_severity: str,
    rationale: str | None = None,
) -> None:
    await record(
        db,
        user_id=user_id,
        decision_type=DecisionType.severity_change,
        decision_data={"old": old_severity, "new": new_severity},
        incident_id=incident_id,
        rationale=rationale,
    )


async def status_changed(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    incident_id: uuid.UUID,
    old_status: str,
    new_status: str,
    rationale: str | None = None,
) -> None:
    await record(
        db,
        user_id=user_id,
        decision_type=DecisionType.status_change,
        decision_data={"old": old_status, "new": new_status},
        incident_id=incident_id,
        rationale=rationale,
    )


async def alert_acknowledged(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    alert_id: uuid.UUID,
    incident_id: uuid.UUID | None = None,
) -> None:
    await record(
        db,
        user_id=user_id,
        decision_type=DecisionType.alert_acknowledged,
        decision_data={"alert_id": str(alert_id)},
        incident_id=incident_id,
    )


async def alert_linked(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    alert_id: uuid.UUID,
    incident_id: uuid.UUID,
) -> None:
    await record(
        db,
        user_id=user_id,
        decision_type=DecisionType.alert_linked,
        decision_data={"alert_id": str(alert_id)},
        incident_id=incident_id,
    )


async def evidence_collected(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    incident_id: uuid.UUID,
    evidence_id: uuid.UUID,
    evidence_type: str,
    evidence_title: str,
) -> None:
    await record(
        db,
        user_id=user_id,
        decision_type=DecisionType.evidence_collected,
        decision_data={
            "evidence_id": str(evidence_id),
            "type": evidence_type,
            "title": evidence_title,
        },
        incident_id=incident_id,
    )


async def endpoint_isolated(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    endpoint_id: uuid.UUID,
    hostname: str,
    incident_id: uuid.UUID | None = None,
    rationale: str | None = None,
) -> None:
    await record(
        db,
        user_id=user_id,
        decision_type=DecisionType.endpoint_isolated,
        decision_data={"endpoint_id": str(endpoint_id), "hostname": hostname},
        incident_id=incident_id,
        rationale=rationale,
    )


async def endpoint_restored(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    endpoint_id: uuid.UUID,
    hostname: str,
    incident_id: uuid.UUID | None = None,
    rationale: str | None = None,
) -> None:
    await record(
        db,
        user_id=user_id,
        decision_type=DecisionType.endpoint_restored,
        decision_data={"endpoint_id": str(endpoint_id), "hostname": hostname},
        incident_id=incident_id,
        rationale=rationale,
    )


async def note_added(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    incident_id: uuid.UUID,
    note_id: uuid.UUID,
) -> None:
    await record(
        db,
        user_id=user_id,
        decision_type=DecisionType.note_added,
        decision_data={"note_id": str(note_id)},
        incident_id=incident_id,
    )
