import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.endpoint import EndpointStatus


class EndpointCreate(BaseModel):
    hostname: str = Field(..., min_length=1, max_length=255)
    wazuh_agent_id: str | None = Field(None, max_length=20)
    ip_address: str | None = Field(None, max_length=45)
    os_platform: str | None = Field(None, max_length=50)
    os_version: str | None = Field(None, max_length=100)
    description: str | None = None
    tags: list = Field(default_factory=list)


class EndpointUpdate(BaseModel):
    hostname: str | None = Field(None, min_length=1, max_length=255)
    ip_address: str | None = None
    os_platform: str | None = None
    os_version: str | None = None
    description: str | None = None
    tags: list | None = None


class EndpointResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    organization_id: uuid.UUID
    wazuh_agent_id: str | None
    hostname: str
    ip_address: str | None
    os_platform: str | None
    os_version: str | None
    agent_version: str | None
    status: EndpointStatus
    last_seen_at: datetime | None
    tags: list
    description: str | None
    created_at: datetime
    updated_at: datetime


class EndpointActionResponse(BaseModel):
    message: str
    action: str
    endpoint_id: uuid.UUID
    new_status: EndpointStatus
