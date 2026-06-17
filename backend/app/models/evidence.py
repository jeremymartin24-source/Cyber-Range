import uuid
from datetime import datetime
from sqlalchemy import String, Text, BigInteger, Boolean, ForeignKey, Enum as SAEnum, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from app.models.base import Base, UUIDMixin, TimestampMixin


class EvidenceType(str, enum.Enum):
    screenshot = "screenshot"
    log_extract = "log_extract"
    alert_export = "alert_export"
    file_hash = "file_hash"
    network_capture = "network_capture"
    process_list = "process_list"
    registry_key = "registry_key"
    email_header = "email_header"
    other = "other"


class Evidence(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "evidence"

    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    collected_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    type: Mapped[EvidenceType] = mapped_column(
        SAEnum(EvidenceType, name="evidence_type"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    structured_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    source_alert_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alerts.id", ondelete="SET NULL"), nullable=True
    )
    source_endpoint_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("endpoints.id", ondelete="SET NULL"), nullable=True
    )
    is_key_evidence: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    incident: Mapped["Incident"] = relationship("Incident", back_populates="evidence")
    collector: Mapped["User"] = relationship("User", foreign_keys=[collected_by])
    source_alert: Mapped["Alert | None"] = relationship("Alert", foreign_keys=[source_alert_id])
    source_endpoint: Mapped["Endpoint | None"] = relationship("Endpoint", foreign_keys=[source_endpoint_id])
