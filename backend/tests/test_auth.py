import pytest
from httpx import AsyncClient
from app.models.user import User


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_admin: User):
    resp = await client.post("/api/v1/auth/login", json={"email": "admin@test.com", "password": "TestPass123!"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == "admin@test.com"
    assert data["user"]["role"] == "admin"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_admin: User):
    resp = await client.post("/api/v1/auth/login", json={"email": "admin@test.com", "password": "wrongpassword"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_user(client: AsyncClient):
    resp = await client.post("/api/v1/auth/login", json={"email": "nobody@test.com", "password": "pass"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient, admin_token: str):
    resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "admin@test.com"


@pytest.mark.asyncio
async def test_get_me_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_logout(client: AsyncClient, admin_token: str):
    resp = await client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_change_password(client: AsyncClient, test_student: User, student_token: str):
    resp = await client.put(
        "/api/v1/auth/me/password",
        json={"current_password": "TestPass123!", "new_password": "NewPass456!"},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp.status_code == 200
    # Restore original password so other tests are not affected
    resp2 = await client.put(
        "/api/v1/auth/me/password",
        json={"current_password": "NewPass456!", "new_password": "TestPass123!"},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp2.status_code == 200


@pytest.mark.asyncio
async def test_change_password_wrong_current(client: AsyncClient, test_admin: User, admin_token: str):
    resp = await client.put(
        "/api/v1/auth/me/password",
        json={"current_password": "wrongpass", "new_password": "NewPass456!"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 400
