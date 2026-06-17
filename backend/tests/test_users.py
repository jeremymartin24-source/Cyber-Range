import pytest
from httpx import AsyncClient

from app.models.user import User


@pytest.mark.asyncio
async def test_list_users_as_admin(
    client: AsyncClient, admin_token: str, test_admin: User, test_student: User
):
    resp = await client.get("/api/v1/users/", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert data["total"] >= 2


@pytest.mark.asyncio
async def test_list_users_as_student_forbidden(client: AsyncClient, student_token: str):
    resp = await client.get("/api/v1/users/", headers={"Authorization": f"Bearer {student_token}"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_own_profile_as_student(
    client: AsyncClient, test_student: User, student_token: str
):
    resp = await client.get(
        f"/api/v1/users/{test_student.id}",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "student@test.com"


@pytest.mark.asyncio
async def test_student_cannot_view_other_user(
    client: AsyncClient, test_admin: User, student_token: str
):
    resp = await client.get(
        f"/api/v1/users/{test_admin.id}",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
