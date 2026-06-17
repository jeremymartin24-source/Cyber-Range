import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.grade import StudentGrade
from app.schemas.grade import GradeCreate, GradeUpdate


class CRUDGrade(CRUDBase[StudentGrade]):
    async def get_by_run(self, db: AsyncSession, scenario_run_id: uuid.UUID) -> list[StudentGrade]:
        result = await db.execute(
            select(StudentGrade)
            .where(StudentGrade.scenario_run_id == scenario_run_id)
            .order_by(StudentGrade.graded_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_run_and_student(
        self,
        db: AsyncSession,
        scenario_run_id: uuid.UUID,
        student_id: uuid.UUID,
    ) -> StudentGrade | None:
        result = await db.execute(
            select(StudentGrade).where(
                StudentGrade.scenario_run_id == scenario_run_id,
                StudentGrade.student_id == student_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_course(self, db: AsyncSession, course_id: uuid.UUID) -> list[StudentGrade]:
        result = await db.execute(
            select(StudentGrade)
            .where(StudentGrade.course_id == course_id)
            .order_by(StudentGrade.graded_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_student_in_course(
        self,
        db: AsyncSession,
        course_id: uuid.UUID,
        student_id: uuid.UUID,
    ) -> list[StudentGrade]:
        result = await db.execute(
            select(StudentGrade)
            .where(
                StudentGrade.course_id == course_id,
                StudentGrade.student_id == student_id,
            )
            .order_by(StudentGrade.graded_at.desc())
        )
        return list(result.scalars().all())

    async def create_grade(
        self,
        db: AsyncSession,
        *,
        scenario_run_id: uuid.UUID,
        course_id: uuid.UUID,
        graded_by: uuid.UUID,
        obj_in: GradeCreate,
    ) -> StudentGrade:
        db_obj = StudentGrade(
            scenario_run_id=scenario_run_id,
            course_id=course_id,
            student_id=obj_in.student_id,
            graded_by=graded_by,
            score=obj_in.score,
            max_score=obj_in.max_score,
            rubric=obj_in.rubric,
            feedback=obj_in.feedback,
            graded_at=datetime.now(UTC),
        )
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update_grade(
        self,
        db: AsyncSession,
        *,
        grade: StudentGrade,
        obj_in: GradeUpdate,
    ) -> StudentGrade:
        data = obj_in.model_dump(exclude_unset=True, exclude_none=True)
        for field, value in data.items():
            setattr(grade, field, value)
        grade.graded_at = datetime.now(UTC)
        db.add(grade)
        await db.flush()
        await db.refresh(grade)
        return grade


grade = CRUDGrade(StudentGrade)
