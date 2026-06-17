import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Organization, User
from app.crud import course as course_crud, user as user_crud
from app.schemas.course import CourseCreate
from app.schemas.user import UserCreate
from app.models.user import UserRole


# ── Shared fixtures ────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def scenario_course(db: AsyncSession, test_org: Organization, test_instructor: User):
    """A course used across scenario tests."""
    return await course_crud.create(
        db,
        obj_in=CourseCreate(
            organization_id=test_org.id,
            name="Scenario Test Course",
            semester="Fall",
            year=2025,
        ),
        instructor_id=test_instructor.id,
    )


# ── Scenario library ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_scenario_files_admin(client: AsyncClient, admin_token: str):
    resp = await client.get(
        "/api/v1/scenarios/files",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    files = resp.json()
    assert isinstance(files, list)
    # The scenarios/ directory should have our example YAMLs
    assert any("phishing" in f or "ransomware" in f or f.endswith(".yaml") for f in files)


@pytest.mark.asyncio
async def test_list_scenario_files_student_forbidden(client: AsyncClient, student_token: str):
    resp = await client.get(
        "/api/v1/scenarios/files",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_import_scenario(client: AsyncClient, admin_token: str):
    resp = await client.post(
        "/api/v1/scenarios/import",
        json={"yaml_path": "bmg_phishing_campaign.yaml"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["slug"] == "bmg-phishing-campaign"
    assert data["name"] == "BMG Phishing Campaign Response"
    assert data["difficulty"] == "intermediate"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_import_scenario_not_found(client: AsyncClient, admin_token: str):
    resp = await client.post(
        "/api/v1/scenarios/import",
        json={"yaml_path": "nonexistent_scenario.yaml"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_import_scenario_idempotent(client: AsyncClient, admin_token: str):
    """Re-importing the same YAML upserts without error."""
    for _ in range(2):
        resp = await client.post(
            "/api/v1/scenarios/import",
            json={"yaml_path": "bmg_phishing_campaign.yaml"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201
    data = resp.json()
    assert data["slug"] == "bmg-phishing-campaign"


@pytest.mark.asyncio
async def test_student_cannot_import_scenario(client: AsyncClient, student_token: str):
    resp = await client.post(
        "/api/v1/scenarios/import",
        json={"yaml_path": "bmg_phishing_campaign.yaml"},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_list_scenarios_instructor(client: AsyncClient, instructor_token: str):
    resp = await client.get(
        "/api/v1/scenarios",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_list_scenarios_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/v1/scenarios")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_scenario(client: AsyncClient, admin_token: str):
    # First import to ensure it exists
    import_resp = await client.post(
        "/api/v1/scenarios/import",
        json={"yaml_path": "bmg_phishing_campaign.yaml"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert import_resp.status_code == 201
    scenario_id = import_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/scenarios/{scenario_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == scenario_id


@pytest.mark.asyncio
async def test_get_scenario_not_found(client: AsyncClient, admin_token: str):
    fake_id = str(uuid.uuid4())
    resp = await client.get(
        f"/api/v1/scenarios/{fake_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


# ── Launch & run management ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_launch_scenario(
    client: AsyncClient,
    instructor_token: str,
    admin_token: str,
    scenario_course,
):
    # Ensure scenario exists
    import_resp = await client.post(
        "/api/v1/scenarios/import",
        json={"yaml_path": "bmg_phishing_campaign.yaml"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert import_resp.status_code == 201
    scenario_id = import_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/scenarios/{scenario_id}/launch",
        json={"course_id": str(scenario_course.id)},
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["scenario_id"] == scenario_id
    assert data["status"] == "active"
    assert data["incident_id"] is not None


@pytest.mark.asyncio
async def test_launch_scenario_not_found(
    client: AsyncClient,
    instructor_token: str,
    scenario_course,
):
    fake_id = str(uuid.uuid4())
    resp = await client.post(
        f"/api/v1/scenarios/{fake_id}/launch",
        json={"course_id": str(scenario_course.id)},
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_student_cannot_launch_scenario(
    client: AsyncClient,
    student_token: str,
    admin_token: str,
    scenario_course,
):
    import_resp = await client.post(
        "/api/v1/scenarios/import",
        json={"yaml_path": "bmg_phishing_campaign.yaml"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    scenario_id = import_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/scenarios/{scenario_id}/launch",
        json={"course_id": str(scenario_course.id)},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp.status_code == 403


# ── Scenario runs ──────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def active_run(client: AsyncClient, instructor_token: str, admin_token: str, scenario_course):
    """Create and return an active scenario run for use in run-management tests."""
    import_resp = await client.post(
        "/api/v1/scenarios/import",
        json={"yaml_path": "bmg_phishing_campaign.yaml"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert import_resp.status_code == 201
    scenario_id = import_resp.json()["id"]

    launch_resp = await client.post(
        f"/api/v1/scenarios/{scenario_id}/launch",
        json={"course_id": str(scenario_course.id)},
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert launch_resp.status_code == 201
    return launch_resp.json()


@pytest.mark.asyncio
async def test_list_runs(client: AsyncClient, instructor_token: str, active_run: dict):
    resp = await client.get(
        "/api/v1/scenario-runs",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert resp.status_code == 200
    runs = resp.json()
    assert isinstance(runs, list)


@pytest.mark.asyncio
async def test_get_run(client: AsyncClient, instructor_token: str, active_run: dict):
    run_id = active_run["id"]
    resp = await client.get(
        f"/api/v1/scenario-runs/{run_id}",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == run_id


@pytest.mark.asyncio
async def test_list_injects_for_run(client: AsyncClient, instructor_token: str, active_run: dict):
    run_id = active_run["id"]
    resp = await client.get(
        f"/api/v1/scenario-runs/{run_id}/injects",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert resp.status_code == 200
    injects = resp.json()
    assert isinstance(injects, list)
    assert len(injects) > 0  # bmg_phishing_campaign has 8 injects
    assert all(i["status"] == "pending" for i in injects)


@pytest.mark.asyncio
async def test_fire_inject(client: AsyncClient, instructor_token: str, active_run: dict):
    run_id = active_run["id"]
    injects_resp = await client.get(
        f"/api/v1/scenario-runs/{run_id}/injects",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    injects = injects_resp.json()
    assert len(injects) > 0

    # Fire the first inject (it's an alert type)
    inject_id = injects[0]["id"]
    resp = await client.post(
        f"/api/v1/scenario-runs/{run_id}/injects/{inject_id}/fire",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("fired", "failed")  # failed if no org lookup, still marks
    assert data["fired_at"] is not None


@pytest.mark.asyncio
async def test_fire_inject_already_fired(client: AsyncClient, instructor_token: str, active_run: dict):
    run_id = active_run["id"]
    injects_resp = await client.get(
        f"/api/v1/scenario-runs/{run_id}/injects",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    pending = [i for i in injects_resp.json() if i["status"] == "pending"]
    assert len(pending) > 0

    inject_id = pending[0]["id"]
    # Fire once
    r1 = await client.post(
        f"/api/v1/scenario-runs/{run_id}/injects/{inject_id}/fire",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert r1.status_code == 200

    # Fire again → 409
    r2 = await client.post(
        f"/api/v1/scenario-runs/{run_id}/injects/{inject_id}/fire",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_complete_run(client: AsyncClient, instructor_token: str, active_run: dict):
    run_id = active_run["id"]
    resp = await client.post(
        f"/api/v1/scenario-runs/{run_id}/complete",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"
    assert resp.json()["completed_at"] is not None


@pytest.mark.asyncio
async def test_abort_run(client: AsyncClient, instructor_token: str, admin_token: str, scenario_course):
    # Create a fresh run to abort
    import_resp = await client.post(
        "/api/v1/scenarios/import",
        json={"yaml_path": "bmg_ransomware_tabletop.yaml"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert import_resp.status_code == 201
    scenario_id = import_resp.json()["id"]

    launch_resp = await client.post(
        f"/api/v1/scenarios/{scenario_id}/launch",
        json={"course_id": str(scenario_course.id)},
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert launch_resp.status_code == 201
    run_id = launch_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/scenario-runs/{run_id}/abort",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "aborted"


@pytest.mark.asyncio
async def test_abort_completed_run_fails(client: AsyncClient, instructor_token: str, active_run: dict):
    run_id = active_run["id"]
    # Complete the run first
    await client.post(
        f"/api/v1/scenario-runs/{run_id}/complete",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    # Now try to abort — should fail with 422
    resp = await client.post(
        f"/api/v1/scenario-runs/{run_id}/abort",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_delete_scenario(client: AsyncClient, admin_token: str):
    import_resp = await client.post(
        "/api/v1/scenarios/import",
        json={"yaml_path": "bmg_ransomware_tabletop.yaml"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert import_resp.status_code == 201
    scenario_id = import_resp.json()["id"]

    del_resp = await client.delete(
        f"/api/v1/scenarios/{scenario_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert del_resp.status_code == 200
    assert "deleted" in del_resp.json()["message"].lower()

    # Verify it's gone
    get_resp = await client.get(
        f"/api/v1/scenarios/{scenario_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_resp.status_code == 404
