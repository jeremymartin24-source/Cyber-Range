import uuid
from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, Enum as SAEnum, JSON
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from app.models.base import Base, UUIDMixin, TimestampMixin


class EndpointStatus(str, enum.Enum):
    active = "active"
    offline = "offline"
    isolated = "isolated"
    decommissioned = "decommissioned"


class Endpoint(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "endpoints"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    wazuh_agent_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    os_platform: Mapped[str | None] = mapped_column(String(50), nullable=True)
    os_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    agent_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[EndpointStatus] = mapped_column(
        SAEnum(EndpointStatus, name="endpoint_status"),
        nullable=False,
        default=EndpointStatus.active,
        server_default="active",
        index=True,
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(nullable=True)
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list, server_default="[]")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    organization: Mapped["Organization"] = relationship("Organization")
    alerts: Mapped[list["Alert"]] = relationship("Alert", back_populates="endpoint")
