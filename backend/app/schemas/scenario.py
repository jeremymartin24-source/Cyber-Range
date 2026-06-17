import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.scenario import InjectStatus, InjectType, ScenarioDifficulty, ScenarioRunStatus


class ScenarioResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    slug: str
    name: str
    version: str
    difficulty: ScenarioDifficulty
    estimated_duration_minutes: int | None
    description: str | None
    objectives: list
    ttps: list
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ScenarioImportRequest(BaseModel):
    yaml_path: str = Field(..., description="Path to YAML file relative to scenarios/ directory")


class ScenarioLaunchRequest(BaseModel):
    course_id: uuid.UUID
    team_id: uuid.UUID | None = None
    settings: dict = Field(default_factory=dict)


class ScenarioRunResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    scenario_id: uuid.UUID
    course_id: uuid.UUID
    team_id: uuid.UUID | None
    incident_id: uuid.UUID | None
    started_by: uuid.UUID
    status: ScenarioRunStatus
    started_at: datetime | None
    completed_at: datetime | None
    settings: dict
    created_at: datetime
    updated_at: datetime


class InjectResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    scenario_run_id: uuid.UUID
    inject_slug: str
    inject_type: InjectType
    scheduled_at: datetime
    fired_at: datetime | None
    status: InjectStatus
    payload: dict
    result: dict | None
    created_at: datetime
