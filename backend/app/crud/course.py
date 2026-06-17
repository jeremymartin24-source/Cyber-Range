import uuid

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.course import Course
from app.models.team import Enrollment, EnrollmentStatus
from app.schemas.course import CourseCreate, CourseUpdate


class CRUDCourse(CRUDBase[Course]):
    async def get_by_organization(
        self, db: AsyncSession, organization_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> list[Course]:
        result = await db.execute(
            select(Course)
            .where(Course.organization_id == organization_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_instructor(self, db: AsyncSession, instructor_id: uuid.UUID) -> list[Course]:
        result = await db.execute(select(Course).where(Course.instructor_id == instructor_id))
        return list(result.scalars().all())

    async def create(
        self, db: AsyncSession, *, obj_in: CourseCreate, instructor_id: uuid.UUID
    ) -> Course:
        db_obj = Course(
            organization_id=obj_in.organization_id,
            instructor_id=instructor_id,
            name=obj_in.name,
            description=obj_in.description,
            semester=obj_in.semester,
            year=obj_in.year,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(self, db: AsyncSession, *, db_obj: Course, obj_in: CourseUpdate) -> Course:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj


class CRUDEnrollment(CRUDBase[Enrollment]):
    async def get_by_course_and_user(
        self, db: AsyncSession, course_id: uuid.UUID, user_id: uuid.UUID
    ) -> Enrollment | None:
        result = await db.execute(
            select(Enrollment).where(
                and_(Enrollment.course_id == course_id, Enrollment.user_id == user_id)
            )
        )
        return result.scalar_one_or_none()

    async def get_by_course(self, db: AsyncSession, course_id: uuid.UUID) -> list[Enrollment]:
        result = await db.execute(
            select(Enrollment).where(
                and_(
                    Enrollment.course_id == course_id,
                    Enrollment.status == EnrollmentStatus.active,
                )
            )
        )
        return list(result.scalars().all())

    async def get_by_user(self, db: AsyncSession, user_id: uuid.UUID) -> list[Enrollment]:
        result = await db.execute(select(Enrollment).where(Enrollment.user_id == user_id))
        return list(result.scalars().all())

    async def enroll(
        self, db: AsyncSession, course_id: uuid.UUID, user_id: uuid.UUID
    ) -> Enrollment:
        db_obj = Enrollment(
            course_id=course_id,
            user_id=user_id,
            status=EnrollmentStatus.active,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update_status(
        self, db: AsyncSession, *, enrollment: Enrollment, status: EnrollmentStatus
    ) -> Enrollment:
        enrollment.status = status
        db.add(enrollment)
        await db.commit()
        await db.refresh(enrollment)
        return enrollment


course = CRUDCourse(Course)
enrollment = CRUDEnrollment(Enrollment)
