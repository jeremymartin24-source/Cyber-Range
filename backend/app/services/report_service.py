"""
Generate scenario run reports and student performance summaries.
"""
import uuid
from collections import Counter
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.grade import grade as grade_crud
from app.crud.scenario import scenario as scenario_crud, scenario_run as run_crud, inject as inject_crud
from app.crud.student_decision import student_decision as decision_crud
from app.crud.user import user as user_crud
from app.models.scenario import ScenarioRunStatus, InjectStatus
from app.schemas.grade import (
    GradeResponse,
    TimelineEvent,
    InjectStats,
    DecisionStats,
    ScenarioRunReport,
    CourseLeaderboardEntry,
    StudentPerformanceReport,
)


async def generate_run_report(db: AsyncSession, run_id: uuid.UUID) -> ScenarioRunReport:
    run = await run_crud.get(db, run_id)
    if not run:
        raise ValueError(f"ScenarioRun {run_id} not found")

    sc = await scenario_crud.get(db, run.scenario_id)
    injects = await inject_crud.get_by_run(db, run_id)

    decisions = []
    if run.incident_id:
        decisions = await decision_crud.get_by_incident(db, run.incident_id)

    # ── Timeline ───────────────────────────────────────────────────────────────
    timeline: list[TimelineEvent] = []

    for inj in injects:
        occurred = inj.fired_at or inj.scheduled_at
        timeline.append(TimelineEvent(
            event_type="inject",
            occurred_at=occurred,
            title=f"[{inj.inject_type.upper()}] {inj.inject_slug}",
            detail={
                "inject_type": inj.inject_type.value,
                "inject_slug": inj.inject_slug,
                "status": inj.status.value,
                "scheduled_at": inj.scheduled_at.isoformat(),
                "payload": inj.payload,
                "result": inj.result,
            },
        ))

    for dec in decisions:
        timeline.append(TimelineEvent(
            event_type="decision",
            occurred_at=dec.decided_at,
            title=f"[DECISION] {dec.decision_type.value}",
            detail={
                "decision_type": dec.decision_type.value,
                "user_id": str(dec.user_id),
                "decision_data": dec.decision_data,
                "rationale": dec.rationale,
                "auto_score": float(dec.auto_score) if dec.auto_score is not None else None,
            },
        ))

    timeline.sort(key=lambda e: e.occurred_at)

    # ── Stats ──────────────────────────────────────────────────────────────────
    inject_status_counts = Counter(i.status.value for i in injects)
    decision_type_counts = Counter(d.decision_type.value for d in decisions)

    duration: float | None = None
    if run.started_at and run.completed_at:
        duration = (run.completed_at - run.started_at).total_seconds() / 60

    # ── Grades ─────────────────────────────────────────────────────────────────
    raw_grades = await grade_crud.get_by_run(db, run_id)
    grades = [GradeResponse.model_validate(g) for g in raw_grades]

    sc_name = sc.name if sc else "Unknown"
    sc_slug = sc.slug if sc else "unknown"
    sc_difficulty = sc.difficulty.value if sc else "intermediate"

    return ScenarioRunReport(
        run_id=run.id,
        scenario_slug=sc_slug,
        scenario_name=sc_name,
        difficulty=sc_difficulty,
        status=run.status.value,
        started_at=run.started_at,
        completed_at=run.completed_at,
        duration_minutes=round(duration, 1) if duration is not None else None,
        injects=InjectStats(
            total=len(injects),
            fired=inject_status_counts.get("fired", 0),
            pending=inject_status_counts.get("pending", 0),
            skipped=inject_status_counts.get("skipped", 0),
            failed=inject_status_counts.get("failed", 0),
        ),
        decisions=DecisionStats(
            total=len(decisions),
            by_type=dict(decision_type_counts),
        ),
        timeline=timeline,
        grades=grades,
    )


async def get_course_leaderboard(
    db: AsyncSession, course_id: uuid.UUID
) -> list[CourseLeaderboardEntry]:
    all_grades = await grade_crud.get_by_course(db, course_id)
    if not all_grades:
        return []

    # Group by student
    student_grades: dict[uuid.UUID, list] = {}
    for g in all_grades:
        student_grades.setdefault(g.student_id, []).append(g)

    entries: list[CourseLeaderboardEntry] = []
    for student_id, grades in student_grades.items():
        student = await user_crud.get(db, student_id)
        name = f"{student.first_name} {student.last_name}" if student else "Unknown"
        email = student.email if student else ""

        scores = [float(g.score) for g in grades]
        avg = round(sum(scores) / len(scores), 1) if scores else 0.0
        highest = max(scores) if scores else 0.0

        # Count decisions for this student in this course
        total_decisions = 0
        for g in grades:
            run = await run_crud.get(db, g.scenario_run_id)
            if run and run.incident_id:
                dec = await decision_crud.get_by_incident_and_user(db, run.incident_id, student_id)
                total_decisions += len(dec)

        entries.append(CourseLeaderboardEntry(
            student_id=student_id,
            student_name=name,
            student_email=email,
            runs_graded=len(grades),
            average_score=avg,
            highest_score=highest,
            total_decisions=total_decisions,
        ))

    entries.sort(key=lambda e: e.average_score, reverse=True)
    return entries


async def get_student_performance(
    db: AsyncSession,
    course_id: uuid.UUID,
    student_id: uuid.UUID,
) -> StudentPerformanceReport:
    student = await user_crud.get(db, student_id)
    name = f"{student.first_name} {student.last_name}" if student else "Unknown"
    email = student.email if student else ""

    grades = await grade_crud.get_by_student_in_course(db, course_id, student_id)
    scores = [float(g.score) for g in grades]
    avg = round(sum(scores) / len(scores), 1) if scores else None

    # Count distinct scenario runs in course where this student has decisions
    from sqlalchemy import select
    from app.models.scenario import ScenarioRun
    result = await db.execute(
        select(ScenarioRun).where(ScenarioRun.course_id == course_id)
    )
    all_runs = list(result.scalars().all())
    participated = 0
    for run in all_runs:
        if run.incident_id:
            dec = await decision_crud.get_by_incident_and_user(db, run.incident_id, student_id)
            if dec:
                participated += 1

    return StudentPerformanceReport(
        student_id=student_id,
        student_name=name,
        student_email=email,
        course_id=course_id,
        runs_participated=participated,
        runs_graded=len(grades),
        average_score=avg,
        grades=[GradeResponse.model_validate(g) for g in grades],
    )
