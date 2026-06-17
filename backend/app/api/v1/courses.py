import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies.auth import get_current_user, require_instructor, require_admin
from app.models.user import User, UserRole
from app.models.team import EnrollmentStatus
from app.crud import course as course_crud, enrollment as enrollment_crud
from app.schemas.course import (
    CourseCreate,
    CourseUpdate,
    CourseResponse,
    EnrollRequest,
    EnrollmentResponse,
)
from app.schemas.common import MessageResponse

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("", response_model=list[CourseResponse])
async def list_courses(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role == UserRole.student:
        enrollments = await enrollment_crud.get_by_user(db, current_user.id)
        course_ids = {e.course_id for e in enrollments}
        all_courses = await course_crud.get_by_organization(
            db, current_user.organization_id, skip=skip, limit=limit
        )
        return [c for c in all_courses if c.id in course_ids]
    if current_user.role == UserRole.instructor:
        return await course_crud.get_by_instructor(db, current_user.id)
    return await course_crud.get_by_organization(
        db, current_user.organization_id, skip=skip, limit=limit
    )


@router.post("", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
async def create_course(
    obj_in: CourseCreate,
    current_user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    return await course_crud.create(db, obj_in=obj_in, instructor_id=current_user.id)


@router.get("/{course_id}", response_model=CourseResponse)
async def get_course(
    course_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    c = await course_crud.get(db, course_id)
    if not c:
        raise HTTPException(status_code=404, detail="Course not found")
    return c


@router.patch("/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: uuid.UUID,
    obj_in: CourseUpdate,
    current_user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    c = await course_crud.get(db, course_id)
    if not c:
        raise HTTPException(status_code=404, detail="Course not found")
    if current_user.role == UserRole.instructor and c.instructor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your course")
    return await course_crud.update(db, db_obj=c, obj_in=obj_in)


@router.delete("/{course_id}", response_model=MessageResponse)
async def delete_course(
    course_id: uuid.UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    c = await course_crud.get(db, course_id)
    if not c:
        raise HTTPException(status_code=404, detail="Course not found")
    await course_crud.delete(db, obj=c)
    return MessageResponse(message="Course deleted")


@router.post("/{course_id}/enroll", response_model=EnrollmentResponse, status_code=status.HTTP_201_CREATED)
async def enroll_student(
    course_id: uuid.UUID,
    obj_in: EnrollRequest,
    current_user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    c = await course_crud.get(db, course_id)
    if not c:
        raise HTTPException(status_code=404, detail="Course not found")
    existing = await enrollment_crud.get_by_course_and_user(db, course_id, obj_in.user_id)
    if existing and existing.status == EnrollmentStatus.active:
        raise HTTPException(status_code=409, detail="User already enrolled")
    if existing:
        return await enrollment_crud.update_status(
            db, enrollment=existing, status=EnrollmentStatus.active
        )
    return await enrollment_crud.enroll(db, course_id, obj_in.user_id)


@router.get("/{course_id}/enrollments", response_model=list[EnrollmentResponse])
async def list_enrollments(
    course_id: uuid.UUID,
    current_user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    c = await course_crud.get(db, course_id)
    if not c:
        raise HTTPException(status_code=404, detail="Course not found")
    return await enrollment_crud.get_by_course(db, course_id)


@router.delete("/{course_id}/enrollments/{user_id}", response_model=MessageResponse)
async def withdraw_student(
    course_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    e = await enrollment_crud.get_by_course_and_user(db, course_id, user_id)
    if not e:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    await enrollment_crud.update_status(db, enrollment=e, status=EnrollmentStatus.withdrawn)
    return MessageResponse(message="Student withdrawn")
