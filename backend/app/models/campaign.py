import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class CampaignRunStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    completed = "completed"
    aborted = "aborted"


class CampaignRunProgressStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    completed = "completed"
    skipped = "skipped"


class Campaign(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "campaigns"

    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    entries: Mapped[list["CampaignScenarioEntry"]] = relationship(
        "CampaignScenarioEntry",
        back_populates="campaign",
        order_by="CampaignScenarioEntry.order_index",
        passive_deletes=True,
    )
    runs: Mapped[list["CampaignRun"]] = relationship(
        "CampaignRun", back_populates="campaign", passive_deletes=True
    )


class CampaignScenarioEntry(Base, UUIDMixin, TimestampMixin):
    """An ordered scenario slot within a Campaign template."""

    __tablename__ = "campaign_scenario_entries"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scenario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scenarios.id", ondelete="RESTRICT"), nullable=False
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    day_offset: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_optional: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="entries")
    scenario: Mapped["Scenario"] = relationship("Scenario")


class CampaignRun(Base, UUIDMixin, TimestampMixin):
    """A running instance of a Campaign for a specific course."""

    __tablename__ = "campaign_runs"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="RESTRICT"),
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
        UUID(as_uuid=True), ForeignKey("teams.id", ondelete="SET NULL"), nullable=True
    )
    started_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[CampaignRunStatus] = mapped_column(
        SAEnum(CampaignRunStatus, name="campaign_run_status"),
        nullable=False,
        default=CampaignRunStatus.draft,
        server_default="draft",
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    settings: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="runs")
    progress: Mapped[list["CampaignRunProgress"]] = relationship(
        "CampaignRunProgress",
        back_populates="campaign_run",
        order_by="CampaignRunProgress.order_index",
        passive_deletes=True,
    )


class CampaignRunProgress(Base, UUIDMixin, TimestampMixin):
    """Tracks whether each scenario entry in a CampaignRun has been run."""

    __tablename__ = "campaign_run_progress"

    campaign_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaign_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    campaign_scenario_entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaign_scenario_entries.id", ondelete="CASCADE"),
        nullable=False,
    )
    scenario_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scenario_runs.id", ondelete="SET NULL"), nullable=True
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[CampaignRunProgressStatus] = mapped_column(
        SAEnum(CampaignRunProgressStatus, name="campaign_run_progress_status"),
        nullable=False,
        default=CampaignRunProgressStatus.pending,
        server_default="pending",
    )

    campaign_run: Mapped["CampaignRun"] = relationship("CampaignRun", back_populates="progress")
    entry: Mapped["CampaignScenarioEntry"] = relationship("CampaignScenarioEntry")
