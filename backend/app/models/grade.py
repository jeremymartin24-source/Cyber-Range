import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class StudentGrade(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "student_grades"
    __table_args__ = (
        UniqueConstraint("scenario_run_id", "student_id", name="uq_grade_run_student"),
    )

    scenario_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scenario_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    graded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    max_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=100)
    rubric: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    graded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    scenario_run: Mapped["ScenarioRun"] = relationship("ScenarioRun")
    student: Mapped["User"] = relationship("User", foreign_keys=[student_id])
    grader: Mapped["User"] = relationship("User", foreign_keys=[graded_by])
