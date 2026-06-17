import uuid
from sqlalchemy import String, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from app.models.base import Base, UUIDMixin, TimestampMixin


class EnrollmentStatus(str, enum.Enum):
    active = "active"
    withdrawn = "withdrawn"
    completed = "completed"


class TeamMemberRole(str, enum.Enum):
    lead = "lead"
    analyst = "analyst"


class Enrollment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "enrollments"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[EnrollmentStatus] = mapped_column(
        SAEnum(EnrollmentStatus, name="enrollment_status"),
        nullable=False,
        default=EnrollmentStatus.active,
        server_default="active",
    )

    user: Mapped["User"] = relationship("User")
    course: Mapped["Course"] = relationship("Course", back_populates="enrollments")


class Team(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "teams"

    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    course: Mapped["Course"] = relationship("Course", back_populates="teams")
    members: Mapped[list["TeamMember"]] = relationship("TeamMember", back_populates="team")


class TeamMember(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "team_members"

    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[TeamMemberRole] = mapped_column(
        SAEnum(TeamMemberRole, name="team_member_role"),
        nullable=False,
        default=TeamMemberRole.analyst,
        server_default="analyst",
    )

    team: Mapped["Team"] = relationship("Team", back_populates="members")
    user: Mapped["User"] = relationship("User")
