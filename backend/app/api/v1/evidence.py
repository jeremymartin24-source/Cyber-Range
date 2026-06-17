import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.crud import evidence as evidence_crud, incident as incident_crud
from app.schemas.evidence import EvidenceCreate, EvidenceUpdate, EvidenceResponse
from app.schemas.common import MessageResponse
from app.services import decision_service

router = APIRouter(prefix="/incidents/{incident_id}/evidence", tags=["evidence"])


async def _get_incident_or_404(incident_id: uuid.UUID, db: AsyncSession):
    inc = await incident_crud.get(db, incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    return inc


@router.get("", response_model=list[EvidenceResponse])
async def list_evidence(
    incident_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_incident_or_404(incident_id, db)
    return await evidence_crud.get_by_incident(db, incident_id)


@router.post("", response_model=EvidenceResponse, status_code=status.HTTP_201_CREATED)
async def add_evidence(
    incident_id: uuid.UUID,
    obj_in: EvidenceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_incident_or_404(incident_id, db)
    ev = await evidence_crud.create(
        db, obj_in=obj_in, incident_id=incident_id, collected_by=current_user.id
    )
    await decision_service.evidence_collected(
        db,
        user_id=current_user.id,
        incident_id=incident_id,
        evidence_id=ev.id,
        evidence_type=ev.type.value,
        evidence_title=ev.title,
    )
    return ev


@router.get("/{evidence_id}", response_model=EvidenceResponse)
async def get_evidence(
    incident_id: uuid.UUID,
    evidence_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_incident_or_404(incident_id, db)
    ev = await evidence_crud.get(db, evidence_id)
    if not ev or ev.incident_id != incident_id:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return ev


@router.patch("/{evidence_id}", response_model=EvidenceResponse)
async def update_evidence(
    incident_id: uuid.UUID,
    evidence_id: uuid.UUID,
    obj_in: EvidenceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_incident_or_404(incident_id, db)
    ev = await evidence_crud.get(db, evidence_id)
    if not ev or ev.incident_id != incident_id:
        raise HTTPException(status_code=404, detail="Evidence not found")
    if ev.collected_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not your evidence")
    return await evidence_crud.update(db, db_obj=ev, obj_in=obj_in)


@router.delete("/{evidence_id}", response_model=MessageResponse)
async def delete_evidence(
    incident_id: uuid.UUID,
    evidence_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_incident_or_404(incident_id, db)
    ev = await evidence_crud.get(db, evidence_id)
    if not ev or ev.incident_id != incident_id:
        raise HTTPException(status_code=404, detail="Evidence not found")
    if ev.collected_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not your evidence")
    await evidence_crud.delete(db, obj=ev)
    return MessageResponse(message="Evidence deleted")
