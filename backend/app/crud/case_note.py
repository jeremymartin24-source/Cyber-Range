import uuid
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.base import CRUDBase
from app.models.case_note import CaseNote
from app.schemas.case_note import CaseNoteCreate, CaseNoteUpdate


class CRUDCaseNote(CRUDBase[CaseNote]):
    async def get_by_incident(
        self,
        db: AsyncSession,
        incident_id: uuid.UUID,
        include_private: bool = False,
        user_id: uuid.UUID | None = None,
    ) -> list[CaseNote]:
        conditions = [CaseNote.incident_id == incident_id]
        if not include_private:
            conditions.append(CaseNote.is_private == False)  # noqa: E712
        elif user_id is not None:
            conditions.append(
                (CaseNote.is_private == False) | (CaseNote.author_id == user_id)  # noqa: E712
            )

        result = await db.execute(
            select(CaseNote)
            .where(and_(*conditions))
            .order_by(CaseNote.is_pinned.desc(), CaseNote.created_at.desc())
        )
        return list(result.scalars().all())

    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: CaseNoteCreate,
        incident_id: uuid.UUID,
        author_id: uuid.UUID,
        is_private: bool = False,
    ) -> CaseNote:
        db_obj = CaseNote(
            incident_id=incident_id,
            author_id=author_id,
            content=obj_in.content,
            is_private=is_private,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self, db: AsyncSession, *, db_obj: CaseNote, obj_in: CaseNoteUpdate
    ) -> CaseNote:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def toggle_pin(self, db: AsyncSession, *, note: CaseNote) -> CaseNote:
        note.is_pinned = not note.is_pinned
        db.add(note)
        await db.commit()
        await db.refresh(note)
        return note


case_note = CRUDCaseNote(CaseNote)
