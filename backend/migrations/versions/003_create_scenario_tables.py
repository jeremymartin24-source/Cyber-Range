"""create scenario tables: scenarios, scenario_runs, injects

Revision ID: 003
Revises: 002
Create Date: 2025-01-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Scenarios ─────────────────────────────────────────────────────────────
    op.create_table(
        "scenarios",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("version", sa.String(20), nullable=False, server_default="1.0.0"),
        sa.Column(
            "difficulty",
            sa.Enum("beginner", "intermediate", "advanced", name="scenario_difficulty"),
            nullable=False,
            server_default="intermediate",
        ),
        sa.Column("estimated_duration_minutes", sa.Integer, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("objectives", JSON, nullable=False, server_default="[]"),
        sa.Column("ttps", JSON, nullable=False, server_default="[]"),
        sa.Column("yaml_content", JSON, nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_scenarios_slug", "scenarios", ["slug"], unique=True)

    # ── Scenario Runs ─────────────────────────────────────────────────────────
    op.create_table(
        "scenario_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("scenario_id", UUID(as_uuid=True), sa.ForeignKey("scenarios.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("course_id", UUID(as_uuid=True), sa.ForeignKey("courses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("team_id", UUID(as_uuid=True), sa.ForeignKey("teams.id", ondelete="SET NULL"), nullable=True),
        sa.Column("incident_id", UUID(as_uuid=True), sa.ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("started_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "active", "completed", "aborted", name="scenario_run_status"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("settings", JSON, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_scenario_runs_scenario_id", "scenario_runs", ["scenario_id"])
    op.create_index("ix_scenario_runs_course_id", "scenario_runs", ["course_id"])
    op.create_index("ix_scenario_runs_team_id", "scenario_runs", ["team_id"])
    op.create_index("ix_scenario_runs_status", "scenario_runs", ["status"])

    # ── Injects ───────────────────────────────────────────────────────────────
    op.create_table(
        "injects",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("scenario_run_id", UUID(as_uuid=True), sa.ForeignKey("scenario_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("inject_slug", sa.String(100), nullable=False),
        sa.Column(
            "inject_type",
            sa.Enum("alert", "endpoint_action", "narrative_update", "hint", name="inject_type"),
            nullable=False,
        ),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "fired", "skipped", "failed", name="inject_status"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("payload", JSON, nullable=False, server_default="{}"),
        sa.Column("result", JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_injects_scenario_run_id", "injects", ["scenario_run_id"])
    op.create_index("ix_injects_inject_type", "injects", ["inject_type"])
    op.create_index("ix_injects_scheduled_at", "injects", ["scheduled_at"])
    op.create_index("ix_injects_status", "injects", ["status"])


def downgrade() -> None:
    op.drop_table("injects")
    op.drop_table("scenario_runs")
    op.drop_table("scenarios")

    op.execute("DROP TYPE IF EXISTS inject_status")
    op.execute("DROP TYPE IF EXISTS inject_type")
    op.execute("DROP TYPE IF EXISTS scenario_run_status")
    op.execute("DROP TYPE IF EXISTS scenario_difficulty")
