"""create campaign tables: campaigns, campaign_scenario_entries, campaign_runs, campaign_run_progress

Revision ID: 005
Revises: 004
Create Date: 2025-01-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enums ─────────────────────────────────────────────────────────────────
    op.execute("CREATE TYPE campaign_run_status AS ENUM ('draft', 'active', 'completed', 'aborted')")
    op.execute("CREATE TYPE campaign_run_progress_status AS ENUM ('pending', 'active', 'completed', 'skipped')")

    # ── Campaigns ─────────────────────────────────────────────────────────────
    op.create_table(
        "campaigns",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_campaigns_slug", "campaigns", ["slug"], unique=True)

    # ── Campaign Scenario Entries ──────────────────────────────────────────────
    op.create_table(
        "campaign_scenario_entries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("campaign_id", UUID(as_uuid=True), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scenario_id", UUID(as_uuid=True), sa.ForeignKey("scenarios.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("order_index", sa.Integer, nullable=False, server_default="0"),
        sa.Column("day_offset", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_optional", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_campaign_scenario_entries_campaign_id", "campaign_scenario_entries", ["campaign_id"])

    # ── Campaign Runs ─────────────────────────────────────────────────────────
    op.create_table(
        "campaign_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("campaign_id", UUID(as_uuid=True), sa.ForeignKey("campaigns.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("course_id", UUID(as_uuid=True), sa.ForeignKey("courses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("team_id", UUID(as_uuid=True), sa.ForeignKey("teams.id", ondelete="SET NULL"), nullable=True),
        sa.Column("started_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column(
            "status",
            sa.Enum("draft", "active", "completed", "aborted", name="campaign_run_status"),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("settings", JSON, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_campaign_runs_campaign_id", "campaign_runs", ["campaign_id"])
    op.create_index("ix_campaign_runs_course_id", "campaign_runs", ["course_id"])
    op.create_index("ix_campaign_runs_status", "campaign_runs", ["status"])

    # ── Campaign Run Progress ─────────────────────────────────────────────────
    op.create_table(
        "campaign_run_progress",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("campaign_run_id", UUID(as_uuid=True), sa.ForeignKey("campaign_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("campaign_scenario_entry_id", UUID(as_uuid=True), sa.ForeignKey("campaign_scenario_entries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scenario_run_id", UUID(as_uuid=True), sa.ForeignKey("scenario_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("order_index", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "status",
            sa.Enum("pending", "active", "completed", "skipped", name="campaign_run_progress_status"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("campaign_run_id", "campaign_scenario_entry_id", name="uq_crp_run_entry"),
    )
    op.create_index("ix_campaign_run_progress_run_id", "campaign_run_progress", ["campaign_run_id"])


def downgrade() -> None:
    op.drop_table("campaign_run_progress")
    op.drop_table("campaign_runs")
    op.drop_table("campaign_scenario_entries")
    op.drop_table("campaigns")
    op.execute("DROP TYPE IF EXISTS campaign_run_progress_status")
    op.execute("DROP TYPE IF EXISTS campaign_run_status")
