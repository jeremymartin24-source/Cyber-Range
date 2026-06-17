import uuid
from sqlalchemy import String, Boolean, Integer, SmallInteger, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from app.models.base import Base, UUIDMixin, TimestampMixin


class CourseStatus(str, enum.Enum):
    active = "active"
    archived = "archived"


class Course(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "courses"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    instructor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    semester: Mapped[str | None] = mapped_column(String(20), nullable=True)
    year: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    organization: Mapped["Organization"] = relationship("Organization")
    instructor: Mapped["User"] = relationship("User", foreign_keys=[instructor_id])
    enrollments: Mapped[list["Enrollment"]] = relationship("Enrollment", back_populates="course")
    teams: Mapped[list["Team"]] = relationship("Team", back_populates="course")
