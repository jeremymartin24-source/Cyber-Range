import uuid
from sqlalchemy import String, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, UUIDMixin, TimestampMixin


class Organization(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    settings: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")

    users: Mapped[list["User"]] = relationship("User", back_populates="organization")
