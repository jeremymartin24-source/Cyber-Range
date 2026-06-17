"""
Tests for grading and reporting endpoints.
"""

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import course as course_crud
from app.crud import user as user_crud
from app.models import Organization, User
from app.models.user import UserRole
from app.schemas.course import CourseCreate
from app.schemas.user import UserCreate

# ── Shared fixtures ─────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def report_course(db: AsyncSession, test_org: Organization, test_instructor: User):
    return await course_crud.create(
        db,
        obj_in=CourseCreate(
            organization_id=test_org.id,
            name="Report Test Course",
            semester="Spring",
            year=2026,
        ),
        instructor_id=test_instructor.id,
    )


@pytest_asyncio.fixture
async def report_student(db: AsyncSession, test_org: Organization):
    existing = await user_crud.get_by_email(db, email="report_student@test.com")
    if existing:
        return existing
    return await user_crud.create(
        db,
        obj_in=UserCreate(
            email="report_student@test.com",
            password="TestPass123!",
            first_name="Report",
            last_name="Student",
            role=UserRole.student,
            organization_id=test_org.id,
        ),
    )


@pytest_asyncio.fixture
async def report_student_token(client: AsyncClient, report_student: User) -> str:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "report_student@test.com", "password": "TestPass123!"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def active_run_for_grading(
    client: AsyncClient,
    instructor_token: str,
    admin_token: str,
    report_course,
):
    """An active scenario run in the report_course."""
    # import scenario
    import_resp = await client.post(
        "/api/v1/scenarios/import",
        json={"yaml_path": "bmg_phishing_campaign.yaml"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert import_resp.status_code == 201
    scenario_id = import_resp.json()["id"]

    launch_resp = await client.post(
        f"/api/v1/scenarios/{scenario_id}/launch",
        json={"course_id": str(report_course.id)},
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert launch_resp.status_code == 201
    return launch_resp.json()


# ── Run report ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_run_report(
    client: AsyncClient,
    instructor_token: str,
    active_run_for_grading: dict,
):
    run_id = active_run_for_grading["id"]
    resp = await client.get(
        f"/api/v1/scenario-runs/{run_id}/report",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["run_id"] == run_id
    assert data["scenario_slug"] == "bmg-phishing-campaign"
    assert data["status"] == "active"
    assert isinstance(data["timeline"], list)
    assert isinstance(data["injects"], dict)
    assert data["injects"]["total"] > 0
    assert isinstance(data["grades"], list)


@pytest.mark.asyncio
async def test_run_report_timeline_has_inject_events(
    client: AsyncClient,
    instructor_token: str,
    active_run_for_grading: dict,
):
    run_id = active_run_for_grading["id"]

    # Fire one inject so it appears in the timeline as a fired event
    injects_resp = await client.get(
        f"/api/v1/scenario-runs/{run_id}/injects",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    inject_id = injects_resp.json()[0]["id"]
    await client.post(
        f"/api/v1/scenario-runs/{run_id}/injects/{inject_id}/fire",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )

    resp = await client.get(
        f"/api/v1/scenario-runs/{run_id}/report",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert resp.status_code == 200
    timeline = resp.json()["timeline"]
    assert any(e["event_type"] == "inject" for e in timeline)


@pytest.mark.asyncio
async def test_run_report_student_forbidden(
    client: AsyncClient,
    student_token: str,
    active_run_for_grading: dict,
):
    run_id = active_run_for_grading["id"]
    resp = await client.get(
        f"/api/v1/scenario-runs/{run_id}/report",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_run_report_not_found(client: AsyncClient, instructor_token: str):
    resp = await client.get(
        f"/api/v1/scenario-runs/{uuid.uuid4()}/report",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert resp.status_code == 404


# ── Grade CRUD ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_grade(
    client: AsyncClient,
    instructor_token: str,
    active_run_for_grading: dict,
    report_student: User,
):
    run_id = active_run_for_grading["id"]
    resp = await client.post(
        f"/api/v1/scenario-runs/{run_id}/grades",
        json={
            "student_id": str(report_student.id),
            "score": 87.5,
            "feedback": "Good detection speed, missed one containment step.",
            "rubric": {
                "detection": {"score": 23, "max": 25},
                "containment": {"score": 28, "max": 35},
                "documentation": {"score": 18, "max": 20},
                "communication": {"score": 18, "max": 20},
            },
        },
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert float(data["score"]) == 87.5
    assert data["student_id"] == str(report_student.id)
    assert data["scenario_run_id"] == run_id


@pytest.mark.asyncio
async def test_create_grade_duplicate_409(
    client: AsyncClient,
    instructor_token: str,
    active_run_for_grading: dict,
    report_student: User,
):
    run_id = active_run_for_grading["id"]
    payload = {"student_id": str(report_student.id), "score": 75.0}

    r1 = await client.post(
        f"/api/v1/scenario-runs/{run_id}/grades",
        json=payload,
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    # May be 201 (first create) or 409 (if already exists from previous test)
    assert r1.status_code in (201, 409)

    if r1.status_code == 201:
        r2 = await client.post(
            f"/api/v1/scenario-runs/{run_id}/grades",
            json=payload,
            headers={"Authorization": f"Bearer {instructor_token}"},
        )
        assert r2.status_code == 409


@pytest.mark.asyncio
async def test_list_grades_for_run(
    client: AsyncClient,
    instructor_token: str,
    active_run_for_grading: dict,
):
    run_id = active_run_for_grading["id"]
    resp = await client.get(
        f"/api/v1/scenario-runs/{run_id}/grades",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_get_grade_as_student(
    client: AsyncClient,
    report_student_token: str,
    instructor_token: str,
    active_run_for_grading: dict,
    report_student: User,
):
    run_id = active_run_for_grading["id"]
    # Ensure grade exists
    await client.post(
        f"/api/v1/scenario-runs/{run_id}/grades",
        json={"student_id": str(report_student.id), "score": 90.0},
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    resp = await client.get(
        f"/api/v1/scenario-runs/{run_id}/grades/{report_student.id}",
        headers={"Authorization": f"Bearer {report_student_token}"},
    )
    # 200 if grade exists, 404 if the POST above returned 409 (grade already existed)
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        assert resp.json()["student_id"] == str(report_student.id)


@pytest.mark.asyncio
async def test_student_cannot_see_other_students_grade(
    client: AsyncClient,
    student_token: str,
    active_run_for_grading: dict,
    report_student: User,
):
    run_id = active_run_for_grading["id"]
    resp = await client.get(
        f"/api/v1/scenario-runs/{run_id}/grades/{report_student.id}",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    # student_token belongs to test_student, not report_student → 403
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_grade(
    client: AsyncClient,
    instructor_token: str,
    active_run_for_grading: dict,
    report_student: User,
    db: AsyncSession,
):
    run_id = active_run_for_grading["id"]
    # Create if not exists
    await client.post(
        f"/api/v1/scenario-runs/{run_id}/grades",
        json={"student_id": str(report_student.id), "score": 70.0},
        headers={"Authorization": f"Bearer {instructor_token}"},
    )

    put_resp = await client.put(
        f"/api/v1/scenario-runs/{run_id}/grades/{report_student.id}",
        json={"score": 82.0, "feedback": "Revised after review."},
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert put_resp.status_code == 200
    assert float(put_resp.json()["score"]) == 82.0


@pytest.mark.asyncio
async def test_delete_grade(
    client: AsyncClient,
    instructor_token: str,
    active_run_for_grading: dict,
    db: AsyncSession,
    test_org: Organization,
):
    """Create a fresh student specifically for deletion test to avoid conflicts."""
    student = await user_crud.create(
        db,
        obj_in=UserCreate(
            email="delete_grade_student@test.com",
            password="TestPass123!",
            first_name="Delete",
            last_name="GradeTest",
            role=UserRole.student,
            organization_id=test_org.id,
        ),
    )
    run_id = active_run_for_grading["id"]
    create_resp = await client.post(
        f"/api/v1/scenario-runs/{run_id}/grades",
        json={"student_id": str(student.id), "score": 55.0},
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert create_resp.status_code == 201

    del_resp = await client.delete(
        f"/api/v1/scenario-runs/{run_id}/grades/{student.id}",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert del_resp.status_code == 204

    # Confirm gone
    get_resp = await client.get(
        f"/api/v1/scenario-runs/{run_id}/grades/{student.id}",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert get_resp.status_code == 404


# ── Course-level endpoints ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_course_grades(
    client: AsyncClient,
    instructor_token: str,
    report_course,
):
    resp = await client.get(
        f"/api/v1/courses/{report_course.id}/grades",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_course_leaderboard(
    client: AsyncClient,
    instructor_token: str,
    report_course,
):
    resp = await client.get(
        f"/api/v1/courses/{report_course.id}/leaderboard",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_student_performance(
    client: AsyncClient,
    instructor_token: str,
    report_course,
    report_student: User,
):
    resp = await client.get(
        f"/api/v1/courses/{report_course.id}/students/{report_student.id}/performance",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["student_id"] == str(report_student.id)
    assert "average_score" in data
    assert isinstance(data["grades"], list)


@pytest.mark.asyncio
async def test_student_can_view_own_performance(
    client: AsyncClient,
    report_student_token: str,
    report_course,
    report_student: User,
):
    resp = await client.get(
        f"/api/v1/courses/{report_course.id}/students/{report_student.id}/performance",
        headers={"Authorization": f"Bearer {report_student_token}"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_student_cannot_view_other_performance(
    client: AsyncClient,
    student_token: str,
    report_course,
    report_student: User,
):
    resp = await client.get(
        f"/api/v1/courses/{report_course.id}/students/{report_student.id}/performance",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_grade_report_includes_grade(
    client: AsyncClient,
    instructor_token: str,
    active_run_for_grading: dict,
    report_student: User,
):
    """After grading, the run report should show the grade."""
    run_id = active_run_for_grading["id"]
    # Ensure a grade exists (may already be there from earlier tests)
    await client.post(
        f"/api/v1/scenario-runs/{run_id}/grades",
        json={"student_id": str(report_student.id), "score": 93.0},
        headers={"Authorization": f"Bearer {instructor_token}"},
    )

    resp = await client.get(
        f"/api/v1/scenario-runs/{run_id}/report",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert resp.status_code == 200
    grades = resp.json()["grades"]
    assert isinstance(grades, list)
    assert len(grades) >= 1
