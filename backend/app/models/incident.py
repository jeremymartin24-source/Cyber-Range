import uuid
from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, Enum as SAEnum, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from app.models.base import Base, UUIDMixin, TimestampMixin


class IncidentSeverity(str, enum.Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    informational = "informational"


class IncidentStatus(str, enum.Enum):
    open = "open"
    investigating = "investigating"
    contained = "contained"
    resolved = "resolved"
    closed = "closed"


# Valid forward transitions
INCIDENT_TRANSITIONS: dict[IncidentStatus, set[IncidentStatus]] = {
    IncidentStatus.open: {IncidentStatus.investigating, IncidentStatus.closed},
    IncidentStatus.investigating: {IncidentStatus.contained, IncidentStatus.closed},
    IncidentStatus.contained: {IncidentStatus.resolved, IncidentStatus.closed},
    IncidentStatus.resolved: {IncidentStatus.closed},
    IncidentStatus.closed: set(),
}


class Incident(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "incidents"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    # scenario_instance_id will be added in Phase 3
    incident_number: Mapped[str] = mapped_column(String(30), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[IncidentSeverity] = mapped_column(
        SAEnum(IncidentSeverity, name="incident_severity"),
        nullable=False,
        default=IncidentSeverity.medium,
        server_default="medium",
        index=True,
    )
    status: Mapped[IncidentStatus] = mapped_column(
        SAEnum(IncidentStatus, name="incident_status"),
        nullable=False,
        default=IncidentStatus.open,
        server_default="open",
        index=True,
    )
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, index=True
    )
    detected_at: Mapped[datetime | None] = mapped_column(nullable=True)
    contained_at: Mapped[datetime | None] = mapped_column(nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    assignee: Mapped["User | None"] = relationship("User", foreign_keys=[assigned_to])
    team: Mapped["Team | None"] = relationship("Team")
    alerts: Mapped[list["IncidentAlert"]] = relationship("IncidentAlert", back_populates="incident")
    evidence: Mapped[list["Evidence"]] = relationship("Evidence", back_populates="incident")
    notes: Mapped[list["CaseNote"]] = relationship("CaseNote", back_populates="incident")
    decisions: Mapped[list["StudentDecision"]] = relationship("StudentDecision", back_populates="incident")
