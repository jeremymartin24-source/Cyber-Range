import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.evidence import EvidenceType


class EvidenceCreate(BaseModel):
    type: EvidenceType
    title: str = Field(..., min_length=2, max_length=255)
    description: str | None = None
    content: str | None = None
    structured_data: dict | None = None
    source_alert_id: uuid.UUID | None = None
    source_endpoint_id: uuid.UUID | None = None
    is_key_evidence: bool = False


class EvidenceUpdate(BaseModel):
    title: str | None = Field(None, min_length=2, max_length=255)
    description: str | None = None
    content: str | None = None
    is_key_evidence: bool | None = None


class EvidenceResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    incident_id: uuid.UUID
    collected_by: uuid.UUID
    type: EvidenceType
    title: str
    description: str | None
    content: str | None
    structured_data: dict | None
    file_path: str | None
    file_size_bytes: int | None
    source_alert_id: uuid.UUID | None
    source_endpoint_id: uuid.UUID | None
    is_key_evidence: bool
    created_at: datetime
    updated_at: datetime
