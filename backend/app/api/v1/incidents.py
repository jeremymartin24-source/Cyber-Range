import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies.auth import get_current_user, require_instructor
from app.models.user import User
from app.crud import incident as incident_crud
from app.schemas.incident import (
    IncidentCreate,
    IncidentUpdate,
    IncidentStatusUpdate,
    IncidentResponse,
)
from app.schemas.common import MessageResponse
from app.services import decision_service

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("", response_model=list[IncidentResponse])
async def list_incidents(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await incident_crud.get_by_organization(
        db, current_user.organization_id, skip=skip, limit=limit
    )


@router.post("", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
async def create_incident(
    obj_in: IncidentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    inc = await incident_crud.create(db, obj_in=obj_in, created_by=current_user.id)
    await decision_service.triage_started(
        db,
        user_id=current_user.id,
        incident_id=inc.id,
        severity=inc.severity.value,
    )
    return inc


@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    inc = await incident_crud.get(db, incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    return inc


@router.patch("/{incident_id}", response_model=IncidentResponse)
async def update_incident(
    incident_id: uuid.UUID,
    obj_in: IncidentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    inc = await incident_crud.get(db, incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    old_severity = inc.severity
    updated = await incident_crud.update(db, db_obj=inc, obj_in=obj_in)

    if obj_in.severity and obj_in.severity != old_severity:
        await decision_service.severity_changed(
            db,
            user_id=current_user.id,
            incident_id=inc.id,
            old_severity=old_severity.value,
            new_severity=obj_in.severity.value,
        )
    return updated


@router.post("/{incident_id}/status", response_model=IncidentResponse)
async def update_status(
    incident_id: uuid.UUID,
    obj_in: IncidentStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    inc = await incident_crud.get(db, incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    old_status = inc.status
    try:
        updated = await incident_crud.transition_status(
            db, incident=inc, new_status=obj_in.status
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    await decision_service.status_changed(
        db,
        user_id=current_user.id,
        incident_id=inc.id,
        old_status=old_status.value,
        new_status=obj_in.status.value,
        rationale=obj_in.rationale,
    )
    return updated


@router.delete("/{incident_id}", response_model=MessageResponse)
async def delete_incident(
    incident_id: uuid.UUID,
    current_user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    inc = await incident_crud.get(db, incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    await incident_crud.delete(db, obj=inc)
    return MessageResponse(message="Incident deleted")
