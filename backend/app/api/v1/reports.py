"""
Grading and reporting endpoints.

Grades are per-student per-run; one instructor can grade multiple students
on the same run.  Reports aggregate the inject timeline and decision audit
trail for post-exercise review.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user, require_instructor
from app.models.user import User, UserRole
from app.crud.grade import grade as grade_crud
from app.crud.scenario import scenario_run as run_crud
from app.schemas.grade import (
    GradeCreate,
    GradeUpdate,
    GradeResponse,
    ScenarioRunReport,
    CourseLeaderboardEntry,
    StudentPerformanceReport,
)
from app.services import report_service

router = APIRouter(tags=["reports"])


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _get_run_or_404(db: AsyncSession, run_id: uuid.UUID):
    run = await run_crud.get(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Scenario run not found")
    return run


# ── Run report ─────────────────────────────────────────────────────────────────

@router.get("/scenario-runs/{run_id}/report", response_model=ScenarioRunReport)
async def get_run_report(
    run_id: uuid.UUID,
    current_user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    await _get_run_or_404(db, run_id)
    try:
        return await report_service.generate_run_report(db, run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ── Grades (sub-resource of scenario-runs) ────────────────────────────────────

@router.get("/scenario-runs/{run_id}/grades", response_model=list[GradeResponse])
async def list_grades_for_run(
    run_id: uuid.UUID,
    current_user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    await _get_run_or_404(db, run_id)
    return await grade_crud.get_by_run(db, run_id)


@router.post(
    "/scenario-runs/{run_id}/grades",
    response_model=GradeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_grade(
    run_id: uuid.UUID,
    obj_in: GradeCreate,
    current_user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    run = await _get_run_or_404(db, run_id)
    existing = await grade_crud.get_by_run_and_student(db, run_id, obj_in.student_id)
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Grade already exists for this student/run. Use PUT to update.",
        )
    grade = await grade_crud.create_grade(
        db,
        scenario_run_id=run_id,
        course_id=run.course_id,
        graded_by=current_user.id,
        obj_in=obj_in,
    )
    await db.commit()
    return grade


@router.get("/scenario-runs/{run_id}/grades/{student_id}", response_model=GradeResponse)
async def get_grade(
    run_id: uuid.UUID,
    student_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Students may only view their own grade; instructors see any
    if current_user.role == UserRole.student and current_user.id != student_id:
        raise HTTPException(status_code=403, detail="Access denied")
    await _get_run_or_404(db, run_id)
    grade = await grade_crud.get_by_run_and_student(db, run_id, student_id)
    if not grade:
        raise HTTPException(status_code=404, detail="Grade not found")
    return grade


@router.put("/scenario-runs/{run_id}/grades/{student_id}", response_model=GradeResponse)
async def update_grade(
    run_id: uuid.UUID,
    student_id: uuid.UUID,
    obj_in: GradeUpdate,
    current_user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    await _get_run_or_404(db, run_id)
    grade = await grade_crud.get_by_run_and_student(db, run_id, student_id)
    if not grade:
        raise HTTPException(status_code=404, detail="Grade not found")
    grade = await grade_crud.update_grade(db, grade=grade, obj_in=obj_in)
    await db.commit()
    return grade


@router.delete(
    "/scenario-runs/{run_id}/grades/{student_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_grade(
    run_id: uuid.UUID,
    student_id: uuid.UUID,
    current_user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    await _get_run_or_404(db, run_id)
    grade = await grade_crud.get_by_run_and_student(db, run_id, student_id)
    if not grade:
        raise HTTPException(status_code=404, detail="Grade not found")
    await grade_crud.delete(db, obj=grade)
    await db.commit()


# ── Course-level reporting ─────────────────────────────────────────────────────

@router.get("/courses/{course_id}/grades", response_model=list[GradeResponse])
async def list_course_grades(
    course_id: uuid.UUID,
    current_user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    return await grade_crud.get_by_course(db, course_id)


@router.get("/courses/{course_id}/leaderboard", response_model=list[CourseLeaderboardEntry])
async def get_course_leaderboard(
    course_id: uuid.UUID,
    current_user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    return await report_service.get_course_leaderboard(db, course_id)


@router.get(
    "/courses/{course_id}/students/{student_id}/performance",
    response_model=StudentPerformanceReport,
)
async def get_student_performance(
    course_id: uuid.UUID,
    student_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role == UserRole.student and current_user.id != student_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return await report_service.get_student_performance(db, course_id, student_id)
