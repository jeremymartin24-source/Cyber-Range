import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, ForeignKey, Numeric, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class DecisionType(str, enum.Enum):
    initial_triage = "initial_triage"
    severity_change = "severity_change"
    status_change = "status_change"
    alert_acknowledged = "alert_acknowledged"
    alert_linked = "alert_linked"
    evidence_collected = "evidence_collected"
    endpoint_isolated = "endpoint_isolated"
    endpoint_restored = "endpoint_restored"
    user_account_disabled = "user_account_disabled"
    escalation = "escalation"
    note_added = "note_added"
    report_submitted = "report_submitted"
    other = "other"


class StudentDecision(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "student_decisions"

    incident_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    decision_type: Mapped[DecisionType] = mapped_column(
        SAEnum(DecisionType, name="decision_type"), nullable=False, index=True
    )
    decision_data: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict, server_default="{}"
    )
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    auto_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    auto_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(nullable=False, default=lambda: datetime.now(UTC))

    incident: Mapped["Incident | None"] = relationship("Incident", back_populates="decisions")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
