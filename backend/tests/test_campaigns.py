import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import course as course_crud
from app.models import Organization, User
from app.schemas.course import CourseCreate

# ── Shared fixtures ────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def campaign_course(db: AsyncSession, test_org: Organization, test_instructor: User):
    return await course_crud.create(
        db,
        obj_in=CourseCreate(
            organization_id=test_org.id,
            name="Campaign Test Course",
            semester="Spring",
            year=2025,
        ),
        instructor_id=test_instructor.id,
    )


@pytest_asyncio.fixture
async def imported_scenario(client: AsyncClient, admin_token: str) -> dict:
    """Import the phishing scenario and return its data."""
    resp = await client.post(
        "/api/v1/scenarios/import",
        json={"yaml_path": "bmg_phishing_campaign.yaml"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    return resp.json()


@pytest_asyncio.fixture
async def campaign(client: AsyncClient, admin_token: str) -> dict:
    """Create a campaign with a unique slug and return its data."""
    slug = f"test-campaign-{uuid.uuid4().hex[:8]}"
    resp = await client.post(
        "/api/v1/campaigns",
        json={"slug": slug, "name": "Test Campaign", "description": "A test campaign"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    return resp.json()


@pytest_asyncio.fixture
async def campaign_with_scenario(
    client: AsyncClient,
    admin_token: str,
    campaign: dict,
    imported_scenario: dict,
) -> dict:
    """Campaign that already has one scenario entry."""
    resp = await client.post(
        f"/api/v1/campaigns/{campaign['id']}/scenarios",
        json={
            "scenario_id": imported_scenario["id"],
            "order_index": 0,
            "day_offset": 0,
            "is_optional": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    return campaign


@pytest_asyncio.fixture
async def campaign_run(
    client: AsyncClient,
    instructor_token: str,
    campaign_with_scenario: dict,
    campaign_course,
) -> dict:
    """A launched campaign run (status=draft, progress rows created)."""
    resp = await client.post(
        f"/api/v1/campaigns/{campaign_with_scenario['id']}/launch",
        json={"course_id": str(campaign_course.id)},
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert resp.status_code == 201
    return resp.json()


# ── Campaign library ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_campaign_admin(client: AsyncClient, admin_token: str):
    resp = await client.post(
        "/api/v1/campaigns",
        json={"slug": "create-test-campaign", "name": "Create Test Campaign"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["slug"] == "create-test-campaign"
    assert data["name"] == "Create Test Campaign"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_create_campaign_instructor_forbidden(client: AsyncClient, instructor_token: str):
    resp = await client.post(
        "/api/v1/campaigns",
        json={"slug": "forbidden-campaign", "name": "Forbidden"},
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_campaign_duplicate_slug(client: AsyncClient, admin_token: str):
    slug = "dup-slug-campaign"
    for _ in range(2):
        resp = await client.post(
            "/api/v1/campaigns",
            json={"slug": slug, "name": "Dup"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_list_campaigns_instructor(
    client: AsyncClient, instructor_token: str, campaign: dict
):
    resp = await client.get(
        "/api/v1/campaigns",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    ids = [c["id"] for c in data]
    assert campaign["id"] in ids


@pytest.mark.asyncio
async def test_list_campaigns_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/v1/campaigns")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_campaign(client: AsyncClient, instructor_token: str, campaign: dict):
    resp = await client.get(
        f"/api/v1/campaigns/{campaign['id']}",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == campaign["id"]


@pytest.mark.asyncio
async def test_get_campaign_not_found(client: AsyncClient, instructor_token: str):
    resp = await client.get(
        f"/api/v1/campaigns/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_campaign(client: AsyncClient, admin_token: str, campaign: dict):
    resp = await client.put(
        f"/api/v1/campaigns/{campaign['id']}",
        json={"name": "Updated Campaign Name", "is_active": False},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Updated Campaign Name"
    assert data["is_active"] is False


@pytest.mark.asyncio
async def test_delete_campaign(client: AsyncClient, admin_token: str):
    create_resp = await client.post(
        "/api/v1/campaigns",
        json={"slug": "delete-me-campaign", "name": "Delete Me"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_resp.status_code == 201
    campaign_id = create_resp.json()["id"]

    del_resp = await client.delete(
        f"/api/v1/campaigns/{campaign_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert del_resp.status_code == 200

    get_resp = await client.get(
        f"/api/v1/campaigns/{campaign_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_resp.status_code == 404


# ── Campaign scenario entries ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_add_scenario_to_campaign(
    client: AsyncClient,
    admin_token: str,
    campaign: dict,
    imported_scenario: dict,
):
    resp = await client.post(
        f"/api/v1/campaigns/{campaign['id']}/scenarios",
        json={
            "scenario_id": imported_scenario["id"],
            "order_index": 0,
            "day_offset": 1,
            "is_optional": True,
            "notes": "Day 1 phishing exercise",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["scenario_id"] == imported_scenario["id"]
    assert data["order_index"] == 0
    assert data["day_offset"] == 1
    assert data["is_optional"] is True
    assert data["notes"] == "Day 1 phishing exercise"


@pytest.mark.asyncio
async def test_add_scenario_to_nonexistent_campaign(
    client: AsyncClient,
    admin_token: str,
    imported_scenario: dict,
):
    resp = await client.post(
        f"/api/v1/campaigns/{uuid.uuid4()}/scenarios",
        json={"scenario_id": imported_scenario["id"], "order_index": 0},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_add_nonexistent_scenario_to_campaign(
    client: AsyncClient,
    admin_token: str,
    campaign: dict,
):
    resp = await client.post(
        f"/api/v1/campaigns/{campaign['id']}/scenarios",
        json={"scenario_id": str(uuid.uuid4()), "order_index": 0},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_campaign_scenarios(
    client: AsyncClient,
    instructor_token: str,
    campaign_with_scenario: dict,
):
    resp = await client.get(
        f"/api/v1/campaigns/{campaign_with_scenario['id']}/scenarios",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_update_campaign_scenario_entry(
    client: AsyncClient,
    admin_token: str,
    campaign_with_scenario: dict,
):
    entries_resp = await client.get(
        f"/api/v1/campaigns/{campaign_with_scenario['id']}/scenarios",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    entry_id = entries_resp.json()[0]["id"]

    resp = await client.put(
        f"/api/v1/campaigns/{campaign_with_scenario['id']}/scenarios/{entry_id}",
        json={"day_offset": 3, "notes": "Updated note"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["day_offset"] == 3
    assert data["notes"] == "Updated note"


@pytest.mark.asyncio
async def test_remove_campaign_scenario_entry(
    client: AsyncClient,
    admin_token: str,
):
    # Create dedicated campaign so we don't disrupt other tests
    c_resp = await client.post(
        "/api/v1/campaigns",
        json={"slug": "remove-entry-campaign", "name": "Remove Entry Test"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    campaign_id = c_resp.json()["id"]

    sc_resp = await client.post(
        "/api/v1/scenarios/import",
        json={"yaml_path": "bmg_ransomware_tabletop.yaml"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    sc_id = sc_resp.json()["id"]

    entry_resp = await client.post(
        f"/api/v1/campaigns/{campaign_id}/scenarios",
        json={"scenario_id": sc_id, "order_index": 0},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    entry_id = entry_resp.json()["id"]

    del_resp = await client.delete(
        f"/api/v1/campaigns/{campaign_id}/scenarios/{entry_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert del_resp.status_code == 204

    entries_resp = await client.get(
        f"/api/v1/campaigns/{campaign_id}/scenarios",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert all(e["id"] != entry_id for e in entries_resp.json())


# ── Campaign launch ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_launch_campaign(
    client: AsyncClient,
    instructor_token: str,
    campaign_with_scenario: dict,
    campaign_course,
):
    resp = await client.post(
        f"/api/v1/campaigns/{campaign_with_scenario['id']}/launch",
        json={"course_id": str(campaign_course.id)},
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["campaign_id"] == campaign_with_scenario["id"]
    assert data["status"] == "draft"
    assert data["course_id"] == str(campaign_course.id)


@pytest.mark.asyncio
async def test_launch_empty_campaign_fails(
    client: AsyncClient,
    admin_token: str,
    instructor_token: str,
    campaign_course,
):
    """Launching a campaign with no scenario entries raises 422."""
    c_resp = await client.post(
        "/api/v1/campaigns",
        json={"slug": "empty-campaign-launch", "name": "Empty"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    campaign_id = c_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/campaigns/{campaign_id}/launch",
        json={"course_id": str(campaign_course.id)},
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_student_cannot_launch_campaign(
    client: AsyncClient,
    student_token: str,
    campaign_with_scenario: dict,
    campaign_course,
):
    resp = await client.post(
        f"/api/v1/campaigns/{campaign_with_scenario['id']}/launch",
        json={"course_id": str(campaign_course.id)},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp.status_code == 403


# ── Campaign runs ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_campaign_runs(
    client: AsyncClient,
    instructor_token: str,
    campaign_run: dict,
):
    resp = await client.get(
        "/api/v1/campaign-runs",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert resp.status_code == 200
    runs = resp.json()
    assert isinstance(runs, list)
    assert any(r["id"] == campaign_run["id"] for r in runs)


@pytest.mark.asyncio
async def test_list_campaign_runs_filter_by_campaign(
    client: AsyncClient,
    instructor_token: str,
    campaign_run: dict,
):
    campaign_id = campaign_run["campaign_id"]
    resp = await client.get(
        f"/api/v1/campaign-runs?campaign_id={campaign_id}",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert resp.status_code == 200
    runs = resp.json()
    assert all(r["campaign_id"] == campaign_id for r in runs)


@pytest.mark.asyncio
async def test_get_campaign_run(
    client: AsyncClient,
    instructor_token: str,
    campaign_run: dict,
):
    resp = await client.get(
        f"/api/v1/campaign-runs/{campaign_run['id']}",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == campaign_run["id"]


@pytest.mark.asyncio
async def test_get_campaign_run_not_found(client: AsyncClient, instructor_token: str):
    resp = await client.get(
        f"/api/v1/campaign-runs/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_campaign_run_progress(
    client: AsyncClient,
    instructor_token: str,
    campaign_run: dict,
):
    resp = await client.get(
        f"/api/v1/campaign-runs/{campaign_run['id']}/progress",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert resp.status_code == 200
    progress = resp.json()
    assert isinstance(progress, list)
    assert len(progress) >= 1
    assert all(p["status"] == "pending" for p in progress)


# ── Campaign run progression ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_launch_next_scenario(
    client: AsyncClient,
    instructor_token: str,
    campaign_run: dict,
    test_instructor: User,
):
    resp = await client.post(
        f"/api/v1/campaign-runs/{campaign_run['id']}/launch-next",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "scenario_run_id" in data
    assert data["status"] == "active"

    # Run should now be active
    run_resp = await client.get(
        f"/api/v1/campaign-runs/{campaign_run['id']}",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert run_resp.json()["status"] == "active"


@pytest.mark.asyncio
async def test_launch_next_when_no_pending_fails(
    client: AsyncClient,
    admin_token: str,
    instructor_token: str,
    campaign_course,
    imported_scenario: dict,
):
    """After all scenarios are launched, launch-next raises 422."""
    # Create dedicated campaign with one scenario
    c_resp = await client.post(
        "/api/v1/campaigns",
        json={"slug": "no-more-pending-campaign", "name": "No More Pending"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    campaign_id = c_resp.json()["id"]
    await client.post(
        f"/api/v1/campaigns/{campaign_id}/scenarios",
        json={"scenario_id": imported_scenario["id"], "order_index": 0},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    launch_resp = await client.post(
        f"/api/v1/campaigns/{campaign_id}/launch",
        json={"course_id": str(campaign_course.id)},
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    run_id = launch_resp.json()["id"]

    # First launch-next succeeds
    r1 = await client.post(
        f"/api/v1/campaign-runs/{run_id}/launch-next",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert r1.status_code == 200

    # Second launch-next fails — no more pending
    r2 = await client.post(
        f"/api/v1/campaign-runs/{run_id}/launch-next",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert r2.status_code == 422


@pytest.mark.asyncio
async def test_skip_scenario(
    client: AsyncClient,
    instructor_token: str,
    campaign_run: dict,
):
    resp = await client.post(
        f"/api/v1/campaign-runs/{campaign_run['id']}/skip",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "skipped"


@pytest.mark.asyncio
async def test_skip_when_no_pending_fails(
    client: AsyncClient,
    admin_token: str,
    instructor_token: str,
    campaign_course,
    imported_scenario: dict,
):
    """After all scenarios are skipped, skip raises 422."""
    c_resp = await client.post(
        "/api/v1/campaigns",
        json={"slug": "skip-all-campaign", "name": "Skip All"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    campaign_id = c_resp.json()["id"]
    await client.post(
        f"/api/v1/campaigns/{campaign_id}/scenarios",
        json={"scenario_id": imported_scenario["id"], "order_index": 0},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    launch_resp = await client.post(
        f"/api/v1/campaigns/{campaign_id}/launch",
        json={"course_id": str(campaign_course.id)},
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    run_id = launch_resp.json()["id"]

    r1 = await client.post(
        f"/api/v1/campaign-runs/{run_id}/skip",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert r1.status_code == 200

    r2 = await client.post(
        f"/api/v1/campaign-runs/{run_id}/skip",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert r2.status_code == 422


@pytest.mark.asyncio
async def test_complete_campaign_run(
    client: AsyncClient,
    instructor_token: str,
    campaign_run: dict,
):
    resp = await client.post(
        f"/api/v1/campaign-runs/{campaign_run['id']}/complete",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["completed_at"] is not None


@pytest.mark.asyncio
async def test_abort_campaign_run(
    client: AsyncClient,
    admin_token: str,
    instructor_token: str,
    campaign_course,
    campaign_with_scenario: dict,
):
    launch_resp = await client.post(
        f"/api/v1/campaigns/{campaign_with_scenario['id']}/launch",
        json={"course_id": str(campaign_course.id)},
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    run_id = launch_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/campaign-runs/{run_id}/abort",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "aborted"


@pytest.mark.asyncio
async def test_complete_already_completed_run_fails(
    client: AsyncClient,
    instructor_token: str,
    campaign_run: dict,
):
    run_id = campaign_run["id"]
    await client.post(
        f"/api/v1/campaign-runs/{run_id}/complete",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    resp = await client.post(
        f"/api/v1/campaign-runs/{run_id}/complete",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert resp.status_code == 422


# ── Campaign run report ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_campaign_run_report(
    client: AsyncClient,
    instructor_token: str,
    campaign_run: dict,
):
    resp = await client.get(
        f"/api/v1/campaign-runs/{campaign_run['id']}/report",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["campaign_run_id"] == campaign_run["id"]
    assert isinstance(data["campaign_name"], str)
    assert isinstance(data["scenarios_total"], int)
    assert data["scenarios_total"] >= 1
    assert isinstance(data["scenarios"], list)
    assert len(data["scenarios"]) == data["scenarios_total"]


@pytest.mark.asyncio
async def test_campaign_run_report_not_found(client: AsyncClient, instructor_token: str):
    resp = await client.get(
        f"/api/v1/campaign-runs/{uuid.uuid4()}/report",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert resp.status_code == 404
