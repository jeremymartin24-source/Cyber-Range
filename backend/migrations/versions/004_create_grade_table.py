"""create student_grades table

Revision ID: 004
Revises: 003
Create Date: 2025-01-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "student_grades",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("scenario_run_id", UUID(as_uuid=True), sa.ForeignKey("scenario_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("course_id", UUID(as_uuid=True), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("graded_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("score", sa.Numeric(5, 2), nullable=False),
        sa.Column("max_score", sa.Numeric(5, 2), nullable=False, server_default="100"),
        sa.Column("rubric", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("feedback", sa.Text, nullable=True),
        sa.Column("graded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("scenario_run_id", "student_id", name="uq_grade_run_student"),
    )
    op.create_index("ix_student_grades_scenario_run_id", "student_grades", ["scenario_run_id"])
    op.create_index("ix_student_grades_course_id", "student_grades", ["course_id"])
    op.create_index("ix_student_grades_student_id", "student_grades", ["student_id"])


def downgrade() -> None:
    op.drop_table("student_grades")
