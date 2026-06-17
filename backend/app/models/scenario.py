import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class ScenarioDifficulty(str, enum.Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class ScenarioRunStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    completed = "completed"
    aborted = "aborted"


class InjectType(str, enum.Enum):
    alert = "alert"
    endpoint_action = "endpoint_action"
    narrative_update = "narrative_update"
    hint = "hint"


class InjectStatus(str, enum.Enum):
    pending = "pending"
    fired = "fired"
    skipped = "skipped"
    failed = "failed"


class Scenario(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "scenarios"

    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0.0")
    difficulty: Mapped[ScenarioDifficulty] = mapped_column(
        SAEnum(ScenarioDifficulty, name="scenario_difficulty"),
        nullable=False,
        default=ScenarioDifficulty.intermediate,
    )
    estimated_duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    objectives: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list, server_default="[]"
    )
    ttps: Mapped[list] = mapped_column(JSON, nullable=False, default=list, server_default="[]")
    yaml_content: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict, server_default="{}"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    runs: Mapped[list["ScenarioRun"]] = relationship(
        "ScenarioRun", back_populates="scenario", passive_deletes=True
    )


class ScenarioRun(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "scenario_runs"

    scenario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scenarios.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, index=True
    )
    incident_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True
    )
    started_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[ScenarioRunStatus] = mapped_column(
        SAEnum(ScenarioRunStatus, name="scenario_run_status"),
        nullable=False,
        default=ScenarioRunStatus.pending,
        server_default="pending",
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    settings: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")

    scenario: Mapped["Scenario"] = relationship("Scenario", back_populates="runs")
    injects: Mapped[list["Inject"]] = relationship("Inject", back_populates="scenario_run")


class Inject(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "injects"

    scenario_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scenario_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    inject_slug: Mapped[str] = mapped_column(String(100), nullable=False)
    inject_type: Mapped[InjectType] = mapped_column(
        SAEnum(InjectType, name="inject_type"),
        nullable=False,
        index=True,
    )
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    fired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[InjectStatus] = mapped_column(
        SAEnum(InjectStatus, name="inject_status"),
        nullable=False,
        default=InjectStatus.pending,
        server_default="pending",
        index=True,
    )
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    scenario_run: Mapped["ScenarioRun"] = relationship("ScenarioRun", back_populates="injects")
