import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CourseBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: str | None = None
    semester: str | None = Field(None, max_length=20)
    year: int | None = Field(None, ge=2000, le=2100)


class CourseCreate(CourseBase):
    organization_id: uuid.UUID


class CourseUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=255)
    description: str | None = None
    semester: str | None = None
    year: int | None = None
    is_active: bool | None = None


class CourseResponse(CourseBase):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    organization_id: uuid.UUID
    instructor_id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime


class EnrollRequest(BaseModel):
    user_id: uuid.UUID


class EnrollmentResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    course_id: uuid.UUID
    status: str
    created_at: datetime
