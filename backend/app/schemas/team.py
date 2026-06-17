import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.team import TeamMemberRole


class TeamCreate(BaseModel):
    course_id: uuid.UUID
    name: str = Field(..., min_length=1, max_length=100)


class TeamUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)


class TeamMemberAdd(BaseModel):
    user_id: uuid.UUID
    role: TeamMemberRole = TeamMemberRole.analyst


class TeamMemberResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    team_id: uuid.UUID
    user_id: uuid.UUID
    role: TeamMemberRole
    created_at: datetime


class TeamResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    course_id: uuid.UUID
    name: str
    created_at: datetime
    updated_at: datetime
