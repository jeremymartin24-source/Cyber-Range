import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.campaign import CampaignRunProgressStatus, CampaignRunStatus


class CampaignCreate(BaseModel):
    slug: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class CampaignUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    is_active: bool | None = None


class CampaignScenarioEntryCreate(BaseModel):
    scenario_id: uuid.UUID
    order_index: int = Field(0, ge=0)
    day_offset: int = Field(
        0, ge=0, description="Days after campaign start to suggest launching this scenario"
    )
    is_optional: bool = False
    notes: str | None = None


class CampaignScenarioEntryUpdate(BaseModel):
    order_index: int | None = Field(None, ge=0)
    day_offset: int | None = Field(None, ge=0)
    is_optional: bool | None = None
    notes: str | None = None


class CampaignScenarioEntryResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    campaign_id: uuid.UUID
    scenario_id: uuid.UUID
    order_index: int
    day_offset: int
    is_optional: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime


class CampaignResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    slug: str
    name: str
    description: str | None
    is_active: bool
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class CampaignLaunchRequest(BaseModel):
    course_id: uuid.UUID
    team_id: uuid.UUID | None = None
    settings: dict = Field(default_factory=dict)


class CampaignRunProgressResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    campaign_run_id: uuid.UUID
    campaign_scenario_entry_id: uuid.UUID
    scenario_run_id: uuid.UUID | None
    order_index: int
    status: CampaignRunProgressStatus
    created_at: datetime
    updated_at: datetime


class CampaignRunResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    campaign_id: uuid.UUID
    course_id: uuid.UUID
    team_id: uuid.UUID | None
    started_by: uuid.UUID
    status: CampaignRunStatus
    started_at: datetime | None
    completed_at: datetime | None
    settings: dict
    created_at: datetime
    updated_at: datetime


class CampaignRunScenarioSummary(BaseModel):
    order_index: int
    campaign_scenario_entry_id: uuid.UUID
    scenario_id: uuid.UUID
    scenario_name: str
    scenario_slug: str
    is_optional: bool
    progress_status: str
    scenario_run_id: uuid.UUID | None
    scenario_run_status: str | None
    decisions_count: int


class CampaignRunReport(BaseModel):
    campaign_run_id: uuid.UUID
    campaign_name: str
    campaign_slug: str
    status: str
    course_id: uuid.UUID
    started_at: datetime | None
    completed_at: datetime | None
    scenarios_total: int
    scenarios_completed: int
    scenarios_pending: int
    scenarios_skipped: int
    total_decisions: int
    scenarios: list[CampaignRunScenarioSummary]
