import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class CaseNoteCreate(BaseModel):
    content: str = Field(..., min_length=1)


class CaseNoteUpdate(BaseModel):
    content: str | None = Field(None, min_length=1)


class CaseNoteResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    incident_id: uuid.UUID
    author_id: uuid.UUID
    content: str
    is_pinned: bool
    is_private: bool
    created_at: datetime
    updated_at: datetime
