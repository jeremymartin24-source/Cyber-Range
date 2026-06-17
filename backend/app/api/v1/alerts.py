import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import alert as alert_crud
from app.crud import incident as incident_crud
from app.database import get_db
from app.dependencies.auth import get_current_user, require_instructor
from app.models.user import User
from app.schemas.alert import AlertCreate, AlertLinkRequest, AlertResponse
from app.schemas.common import MessageResponse
from app.services import decision_service

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertResponse])
async def list_alerts(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await alert_crud.get_by_organization(
        db, current_user.organization_id, skip=skip, limit=limit
    )


@router.post("", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(
    obj_in: AlertCreate,
    current_user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    return await alert_crud.create(db, obj_in=obj_in)


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    a = await alert_crud.get(db, alert_id)
    if not a:
        raise HTTPException(status_code=404, detail="Alert not found")
    return a


@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(
    alert_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    a = await alert_crud.get(db, alert_id)
    if not a:
        raise HTTPException(status_code=404, detail="Alert not found")
    if a.is_acknowledged:
        raise HTTPException(status_code=409, detail="Alert already acknowledged")
    updated = await alert_crud.acknowledge(db, alert=a, user_id=current_user.id)
    await decision_service.alert_acknowledged(db, user_id=current_user.id, alert_id=alert_id)
    return updated


@router.post("/{alert_id}/link", response_model=MessageResponse)
async def link_to_incident(
    alert_id: uuid.UUID,
    obj_in: AlertLinkRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    a = await alert_crud.get(db, alert_id)
    if not a:
        raise HTTPException(status_code=404, detail="Alert not found")
    inc = await incident_crud.get(db, obj_in.incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    existing = await alert_crud.get_link(db, alert_id, obj_in.incident_id)
    if existing:
        raise HTTPException(status_code=409, detail="Alert already linked to incident")
    await alert_crud.link_to_incident(db, alert_id, obj_in.incident_id, linked_by=current_user.id)
    await decision_service.alert_linked(
        db,
        user_id=current_user.id,
        alert_id=alert_id,
        incident_id=obj_in.incident_id,
    )
    return MessageResponse(message="Alert linked to incident")
