import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.incident import IncidentSeverity, IncidentStatus


class IncidentCreate(BaseModel):
    organization_id: uuid.UUID
    title: str = Field(..., min_length=3, max_length=255)
    description: str | None = None
    severity: IncidentSeverity = IncidentSeverity.medium
    category: str | None = Field(None, max_length=50)
    team_id: uuid.UUID | None = None
    assigned_to: uuid.UUID | None = None


class IncidentUpdate(BaseModel):
    title: str | None = Field(None, min_length=3, max_length=255)
    description: str | None = None
    severity: IncidentSeverity | None = None
    category: str | None = None
    team_id: uuid.UUID | None = None
    assigned_to: uuid.UUID | None = None


class IncidentStatusUpdate(BaseModel):
    status: IncidentStatus
    rationale: str | None = None


class IncidentResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    organization_id: uuid.UUID
    incident_number: str
    title: str
    description: str | None
    severity: IncidentSeverity
    status: IncidentStatus
    category: str | None
    assigned_to: uuid.UUID | None
    team_id: uuid.UUID | None
    detected_at: datetime | None
    contained_at: datetime | None
    resolved_at: datetime | None
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime
