import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from pydantic import BaseModel, Field


class GradeCreate(BaseModel):
    student_id: uuid.UUID
    score: float = Field(..., ge=0, le=100)
    max_score: float = Field(100.0, ge=1, le=100)
    rubric: dict = Field(default_factory=dict)
    feedback: str | None = None


class GradeUpdate(BaseModel):
    score: float | None = Field(None, ge=0, le=100)
    max_score: float | None = Field(None, ge=1, le=100)
    rubric: dict | None = None
    feedback: str | None = None


class GradeResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    scenario_run_id: uuid.UUID
    course_id: uuid.UUID
    student_id: uuid.UUID
    graded_by: uuid.UUID
    score: float
    max_score: float
    rubric: dict
    feedback: str | None
    graded_at: datetime
    created_at: datetime
    updated_at: datetime


class TimelineEvent(BaseModel):
    event_type: Literal["inject", "decision"]
    occurred_at: datetime
    title: str
    detail: dict[str, Any]


class InjectStats(BaseModel):
    total: int
    fired: int
    pending: int
    skipped: int
    failed: int


class DecisionStats(BaseModel):
    total: int
    by_type: dict[str, int]


class ScenarioRunReport(BaseModel):
    run_id: uuid.UUID
    scenario_slug: str
    scenario_name: str
    difficulty: str
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    duration_minutes: float | None
    injects: InjectStats
    decisions: DecisionStats
    timeline: list[TimelineEvent]
    grades: list[GradeResponse]


class CourseLeaderboardEntry(BaseModel):
    student_id: uuid.UUID
    student_name: str
    student_email: str
    runs_graded: int
    average_score: float
    highest_score: float
    total_decisions: int


class StudentPerformanceReport(BaseModel):
    student_id: uuid.UUID
    student_name: str
    student_email: str
    course_id: uuid.UUID
    runs_participated: int
    runs_graded: int
    average_score: float | None
    grades: list[GradeResponse]
