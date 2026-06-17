import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Organization, User
from app.crud import course as course_crud, user as user_crud
from app.schemas.course import CourseCreate
from app.schemas.user import UserCreate
from app.models.user import UserRole


@pytest.mark.asyncio
async def test_instructor_can_create_course(client: AsyncClient, db: AsyncSession, test_org: Organization):
    instructor = await user_crud.create(db, obj_in=UserCreate(
        email="instructor_test@test.com",
        password="TestPass123!",
        first_name="John",
        last_name="Doe",
        role=UserRole.instructor,
        organization_id=test_org.id,
    ))
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "instructor_test@test.com", "password": "TestPass123!"},
    )
    token = resp.json()["access_token"]

    resp = await client.post(
        "/api/v1/courses",
        json={
            "organization_id": str(test_org.id),
            "name": "Intro to SOC Operations",
            "semester": "Fall",
            "year": 2025,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Intro to SOC Operations"
    assert data["instructor_id"] == str(instructor.id)


@pytest.mark.asyncio
async def test_student_cannot_create_course(client: AsyncClient, student_token: str, test_org: Organization):
    resp = await client.post(
        "/api/v1/courses",
        json={
            "organization_id": str(test_org.id),
            "name": "Unauthorized Course",
        },
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_list_all_courses(client: AsyncClient, admin_token: str, test_org: Organization, db: AsyncSession):
    instructor = await user_crud.create(db, obj_in=UserCreate(
        email="instructor_list@test.com",
        password="TestPass123!",
        first_name="Jane",
        last_name="Smith",
        role=UserRole.instructor,
        organization_id=test_org.id,
    ))
    await course_crud.create(db, obj_in=CourseCreate(
        organization_id=test_org.id,
        name="Listed Course",
        semester="Spring",
        year=2025,
    ), instructor_id=instructor.id)
    resp = await client.get(
        "/api/v1/courses",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert any(c["name"] == "Listed Course" for c in resp.json())


@pytest.mark.asyncio
async def test_enroll_student(client: AsyncClient, db: AsyncSession, test_org: Organization):
    instructor = await user_crud.create(db, obj_in=UserCreate(
        email="instructor_enroll@test.com",
        password="TestPass123!",
        first_name="Bob",
        last_name="Lee",
        role=UserRole.instructor,
        organization_id=test_org.id,
    ))
    student = await user_crud.create(db, obj_in=UserCreate(
        email="student_enroll@test.com",
        password="TestPass123!",
        first_name="Alice",
        last_name="Green",
        role=UserRole.student,
        organization_id=test_org.id,
    ))
    course = await course_crud.create(db, obj_in=CourseCreate(
        organization_id=test_org.id,
        name="Enrollment Test Course",
    ), instructor_id=instructor.id)

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "instructor_enroll@test.com", "password": "TestPass123!"},
    )
    token = login_resp.json()["access_token"]

    resp = await client.post(
        f"/api/v1/courses/{course.id}/enroll",
        json={"user_id": str(student.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["user_id"] == str(student.id)
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_get_course_not_found(client: AsyncClient, admin_token: str):
    import uuid
    fake_id = uuid.uuid4()
    resp = await client.get(
        f"/api/v1/courses/{fake_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404
