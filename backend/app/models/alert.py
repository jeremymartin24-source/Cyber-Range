import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, ForeignKey, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Alert(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "alerts"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    wazuh_alert_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True, index=True
    )
    is_simulated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    rule_id: Mapped[int | None] = mapped_column(nullable=True)
    rule_level: Mapped[int | None] = mapped_column(SmallInteger, nullable=True, index=True)
    rule_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    rule_groups: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list, server_default="[]"
    )

    agent_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    agent_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    endpoint_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("endpoints.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    raw_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")
    timestamp: Mapped[datetime] = mapped_column(nullable=False, index=True)

    is_acknowledged: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(nullable=True)

    endpoint: Mapped["Endpoint | None"] = relationship("Endpoint", back_populates="alerts")
    acknowledger: Mapped["User | None"] = relationship("User", foreign_keys=[acknowledged_by])
    incident_links: Mapped[list["IncidentAlert"]] = relationship(
        "IncidentAlert", back_populates="alert"
    )


class IncidentAlert(Base, UUIDMixin):
    __tablename__ = "incident_alerts"

    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    linked_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    linked_at: Mapped[datetime] = mapped_column(nullable=False)

    from datetime import datetime as _datetime
    from datetime import timezone as _tz

    incident: Mapped["Incident"] = relationship("Incident", back_populates="alerts")
    alert: Mapped["Alert"] = relationship("Alert", back_populates="incident_links")
    linker: Mapped["User | None"] = relationship("User", foreign_keys=[linked_by])
