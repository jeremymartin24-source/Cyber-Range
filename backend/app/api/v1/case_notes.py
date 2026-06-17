import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User, UserRole
from app.crud import case_note as note_crud, incident as incident_crud
from app.schemas.case_note import CaseNoteCreate, CaseNoteUpdate, CaseNoteResponse
from app.schemas.common import MessageResponse
from app.services import decision_service

router = APIRouter(prefix="/incidents/{incident_id}/notes", tags=["case-notes"])


async def _get_incident_or_404(incident_id: uuid.UUID, db: AsyncSession):
    inc = await incident_crud.get(db, incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    return inc


@router.get("", response_model=list[CaseNoteResponse])
async def list_notes(
    incident_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_incident_or_404(incident_id, db)
    include_private = current_user.role in (UserRole.admin, UserRole.instructor)
    return await note_crud.get_by_incident(
        db,
        incident_id,
        include_private=include_private,
        user_id=current_user.id,
    )


@router.post("", response_model=CaseNoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(
    incident_id: uuid.UUID,
    obj_in: CaseNoteCreate,
    is_private: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_incident_or_404(incident_id, db)
    note = await note_crud.create(
        db,
        obj_in=obj_in,
        incident_id=incident_id,
        author_id=current_user.id,
        is_private=is_private,
    )
    await decision_service.note_added(
        db, user_id=current_user.id, incident_id=incident_id, note_id=note.id
    )
    return note


@router.get("/{note_id}", response_model=CaseNoteResponse)
async def get_note(
    incident_id: uuid.UUID,
    note_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_incident_or_404(incident_id, db)
    note = await note_crud.get(db, note_id)
    if not note or note.incident_id != incident_id:
        raise HTTPException(status_code=404, detail="Note not found")
    if note.is_private and note.author_id != current_user.id and current_user.role == UserRole.student:
        raise HTTPException(status_code=403, detail="Note not found")
    return note


@router.patch("/{note_id}", response_model=CaseNoteResponse)
async def update_note(
    incident_id: uuid.UUID,
    note_id: uuid.UUID,
    obj_in: CaseNoteUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_incident_or_404(incident_id, db)
    note = await note_crud.get(db, note_id)
    if not note or note.incident_id != incident_id:
        raise HTTPException(status_code=404, detail="Note not found")
    if note.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your note")
    return await note_crud.update(db, db_obj=note, obj_in=obj_in)


@router.post("/{note_id}/pin", response_model=CaseNoteResponse)
async def toggle_pin(
    incident_id: uuid.UUID,
    note_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_incident_or_404(incident_id, db)
    note = await note_crud.get(db, note_id)
    if not note or note.incident_id != incident_id:
        raise HTTPException(status_code=404, detail="Note not found")
    if note.author_id != current_user.id and current_user.role == UserRole.student:
        raise HTTPException(status_code=403, detail="Not your note")
    return await note_crud.toggle_pin(db, note=note)


@router.delete("/{note_id}", response_model=MessageResponse)
async def delete_note(
    incident_id: uuid.UUID,
    note_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_incident_or_404(incident_id, db)
    note = await note_crud.get(db, note_id)
    if not note or note.incident_id != incident_id:
        raise HTTPException(status_code=404, detail="Note not found")
    if note.author_id != current_user.id and current_user.role == UserRole.student:
        raise HTTPException(status_code=403, detail="Not your note")
    await note_crud.delete(db, obj=note)
    return MessageResponse(message="Note deleted")
