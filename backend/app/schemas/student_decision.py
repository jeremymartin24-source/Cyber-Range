import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.student_decision import DecisionType


class StudentDecisionResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    incident_id: uuid.UUID | None
    user_id: uuid.UUID
    decision_type: DecisionType
    decision_data: dict
    rationale: str | None
    auto_score: float | None
    auto_feedback: str | None
    decided_at: datetime
    created_at: datetime
