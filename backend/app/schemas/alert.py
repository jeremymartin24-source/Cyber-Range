import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class AlertCreate(BaseModel):
    organization_id: uuid.UUID
    wazuh_alert_id: str | None = None
    rule_id: int | None = None
    rule_level: int | None = Field(None, ge=0, le=15)
    rule_description: str | None = None
    rule_groups: list[str] = Field(default_factory=list)
    agent_id: str | None = None
    agent_name: str | None = None
    endpoint_id: uuid.UUID | None = None
    raw_data: dict = Field(default_factory=dict)
    timestamp: datetime
    is_simulated: bool = False


class AlertLinkRequest(BaseModel):
    incident_id: uuid.UUID


class AlertResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    organization_id: uuid.UUID
    wazuh_alert_id: str | None
    is_simulated: bool
    rule_id: int | None
    rule_level: int | None
    rule_description: str | None
    rule_groups: list
    agent_id: str | None
    agent_name: str | None
    endpoint_id: uuid.UUID | None
    raw_data: dict
    timestamp: datetime
    is_acknowledged: bool
    acknowledged_by: uuid.UUID | None
    acknowledged_at: datetime | None
    created_at: datetime
