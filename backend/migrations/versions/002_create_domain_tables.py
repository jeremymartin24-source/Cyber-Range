"""create domain tables: courses, teams, endpoints, incidents, alerts, evidence, notes, decisions

Revision ID: 002
Revises: 001
Create Date: 2025-01-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Incident number sequence ───────────────────────────────────────────────
    op.execute("CREATE SEQUENCE incident_number_seq START 1")

    # ── Courses ───────────────────────────────────────────────────────────────
    op.create_table(
        "courses",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("instructor_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("semester", sa.String(20), nullable=True),
        sa.Column("year", sa.SmallInteger, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_courses_organization_id", "courses", ["organization_id"])

    # ── Enrollments ───────────────────────────────────────────────────────────
    op.create_table(
        "enrollments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("course_id", UUID(as_uuid=True), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.Enum("active", "withdrawn", "completed", name="enrollment_status"), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "course_id", name="uq_enrollments_user_course"),
    )
    op.create_index("ix_enrollments_user_id", "enrollments", ["user_id"])
    op.create_index("ix_enrollments_course_id", "enrollments", ["course_id"])

    # ── Teams ─────────────────────────────────────────────────────────────────
    op.create_table(
        "teams",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("course_id", UUID(as_uuid=True), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("course_id", "name", name="uq_teams_course_name"),
    )
    op.create_index("ix_teams_course_id", "teams", ["course_id"])

    op.create_table(
        "team_members",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("team_id", UUID(as_uuid=True), sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.Enum("lead", "analyst", name="team_member_role"), nullable=False, server_default="analyst"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("team_id", "user_id", name="uq_team_members_team_user"),
    )
    op.create_index("ix_team_members_team_id", "team_members", ["team_id"])
    op.create_index("ix_team_members_user_id", "team_members", ["user_id"])

    # ── Endpoints ─────────────────────────────────────────────────────────────
    op.create_table(
        "endpoints",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("wazuh_agent_id", sa.String(20), nullable=True),
        sa.Column("hostname", sa.String(255), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("os_platform", sa.String(50), nullable=True),
        sa.Column("os_version", sa.String(100), nullable=True),
        sa.Column("agent_version", sa.String(50), nullable=True),
        sa.Column("status", sa.Enum("active", "offline", "isolated", "decommissioned", name="endpoint_status"), nullable=False, server_default="active"),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tags", JSON, nullable=False, server_default="[]"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_endpoints_organization_id", "endpoints", ["organization_id"])
    op.create_index("ix_endpoints_hostname", "endpoints", ["hostname"])
    op.create_index("ix_endpoints_status", "endpoints", ["status"])

    # ── Incidents ─────────────────────────────────────────────────────────────
    op.create_table(
        "incidents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("incident_number", sa.String(30), nullable=False, unique=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("severity", sa.Enum("critical", "high", "medium", "low", "informational", name="incident_severity"), nullable=False, server_default="medium"),
        sa.Column("status", sa.Enum("open", "investigating", "contained", "resolved", "closed", name="incident_status"), nullable=False, server_default="open"),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("assigned_to", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("team_id", UUID(as_uuid=True), sa.ForeignKey("teams.id", ondelete="SET NULL"), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("contained_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_incidents_incident_number", "incidents", ["incident_number"], unique=True)
    op.create_index("ix_incidents_organization_id", "incidents", ["organization_id"])
    op.create_index("ix_incidents_status", "incidents", ["status"])
    op.create_index("ix_incidents_severity", "incidents", ["severity"])
    op.create_index("ix_incidents_team_id", "incidents", ["team_id"])

    # ── Alerts ────────────────────────────────────────────────────────────────
    op.create_table(
        "alerts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("wazuh_alert_id", sa.String(255), nullable=True, unique=True),
        sa.Column("is_simulated", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("rule_id", sa.Integer, nullable=True),
        sa.Column("rule_level", sa.SmallInteger, nullable=True),
        sa.Column("rule_description", sa.Text, nullable=True),
        sa.Column("rule_groups", JSON, nullable=False, server_default="[]"),
        sa.Column("agent_id", sa.String(20), nullable=True),
        sa.Column("agent_name", sa.String(255), nullable=True),
        sa.Column("endpoint_id", UUID(as_uuid=True), sa.ForeignKey("endpoints.id", ondelete="SET NULL"), nullable=True),
        sa.Column("raw_data", JSON, nullable=False, server_default="{}"),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_acknowledged", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("acknowledged_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_alerts_organization_id", "alerts", ["organization_id"])
    op.create_index("ix_alerts_wazuh_alert_id", "alerts", ["wazuh_alert_id"], unique=True)
    op.create_index("ix_alerts_timestamp", "alerts", ["timestamp"])
    op.create_index("ix_alerts_rule_level", "alerts", ["rule_level"])
    op.create_index("ix_alerts_agent_name", "alerts", ["agent_name"])
    op.create_index("ix_alerts_endpoint_id", "alerts", ["endpoint_id"])

    op.create_table(
        "incident_alerts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("incident_id", UUID(as_uuid=True), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("alert_id", UUID(as_uuid=True), sa.ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("linked_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("incident_id", "alert_id", name="uq_incident_alerts"),
    )
    op.create_index("ix_incident_alerts_incident_id", "incident_alerts", ["incident_id"])
    op.create_index("ix_incident_alerts_alert_id", "incident_alerts", ["alert_id"])

    # ── Evidence ──────────────────────────────────────────────────────────────
    op.create_table(
        "evidence",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("incident_id", UUID(as_uuid=True), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("collected_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("type", sa.Enum("screenshot", "log_extract", "alert_export", "file_hash", "network_capture", "process_list", "registry_key", "email_header", "other", name="evidence_type"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("content", sa.Text, nullable=True),
        sa.Column("structured_data", JSON, nullable=True),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=True),
        sa.Column("source_alert_id", UUID(as_uuid=True), sa.ForeignKey("alerts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source_endpoint_id", UUID(as_uuid=True), sa.ForeignKey("endpoints.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_key_evidence", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_evidence_incident_id", "evidence", ["incident_id"])
    op.create_index("ix_evidence_type", "evidence", ["type"])

    # ── Case Notes ────────────────────────────────────────────────────────────
    op.create_table(
        "case_notes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("incident_id", UUID(as_uuid=True), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("is_pinned", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_private", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_case_notes_incident_id", "case_notes", ["incident_id"])

    # ── Student Decisions ─────────────────────────────────────────────────────
    op.create_table(
        "student_decisions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("incident_id", UUID(as_uuid=True), sa.ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("decision_type", sa.Enum("initial_triage", "severity_change", "status_change", "alert_acknowledged", "alert_linked", "evidence_collected", "endpoint_isolated", "endpoint_restored", "user_account_disabled", "escalation", "note_added", "report_submitted", "other", name="decision_type"), nullable=False),
        sa.Column("decision_data", JSON, nullable=False, server_default="{}"),
        sa.Column("rationale", sa.Text, nullable=True),
        sa.Column("auto_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("auto_feedback", sa.Text, nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_student_decisions_incident_id", "student_decisions", ["incident_id"])
    op.create_index("ix_student_decisions_user_id", "student_decisions", ["user_id"])
    op.create_index("ix_student_decisions_decision_type", "student_decisions", ["decision_type"])
    op.create_index("ix_student_decisions_decided_at", "student_decisions", ["decided_at"])


def downgrade() -> None:
    op.drop_table("student_decisions")
    op.drop_table("case_notes")
    op.drop_table("evidence")
    op.drop_table("incident_alerts")
    op.drop_table("alerts")
    op.drop_table("incidents")
    op.drop_table("endpoints")
    op.drop_table("team_members")
    op.drop_table("teams")
    op.drop_table("enrollments")
    op.drop_table("courses")
    op.execute("DROP SEQUENCE IF EXISTS incident_number_seq")
    op.execute("DROP TYPE IF EXISTS decision_type")
    op.execute("DROP TYPE IF EXISTS evidence_type")
    op.execute("DROP TYPE IF EXISTS incident_status")
    op.execute("DROP TYPE IF EXISTS incident_severity")
    op.execute("DROP TYPE IF EXISTS endpoint_status")
    op.execute("DROP TYPE IF EXISTS team_member_role")
    op.execute("DROP TYPE IF EXISTS enrollment_status")
