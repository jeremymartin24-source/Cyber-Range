import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import student_decision as decision_crud
from app.database import get_db
from app.dependencies.auth import get_current_user, require_instructor
from app.models.user import User
from app.schemas.student_decision import StudentDecisionResponse

router = APIRouter(prefix="/decisions", tags=["decisions"])


@router.get("", response_model=list[StudentDecisionResponse])
async def list_my_decisions(
    incident_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if incident_id:
        return await decision_crud.get_by_incident_and_user(db, incident_id, current_user.id)
    return await decision_crud.get_by_user(db, current_user.id)


@router.get("/incident/{incident_id}", response_model=list[StudentDecisionResponse])
async def list_incident_decisions(
    incident_id: uuid.UUID,
    current_user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    return await decision_crud.get_by_incident(db, incident_id)


@router.get("/user/{user_id}", response_model=list[StudentDecisionResponse])
async def list_user_decisions(
    user_id: uuid.UUID,
    current_user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    return await decision_crud.get_by_user(db, user_id)
