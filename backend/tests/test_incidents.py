import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Organization, User
from app.crud import incident as incident_crud
from app.schemas.incident import IncidentCreate
from app.models.incident import IncidentSeverity, IncidentStatus


@pytest.mark.asyncio
async def test_create_incident(client: AsyncClient, admin_token: str, test_org: Organization):
    resp = await client.post(
        "/api/v1/incidents",
        json={
            "organization_id": str(test_org.id),
            "title": "Suspicious Login Activity",
            "description": "Multiple failed logins from unknown IP",
            "severity": "high",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Suspicious Login Activity"
    assert data["severity"] == "high"
    assert data["status"] == "open"
    assert data["incident_number"].startswith("INC-")


@pytest.mark.asyncio
async def test_list_incidents(client: AsyncClient, admin_token: str, test_org: Organization, db: AsyncSession):
    await incident_crud.create(db, obj_in=IncidentCreate(
        organization_id=test_org.id,
        title="Test Incident",
        severity=IncidentSeverity.medium,
    ), created_by=test_org.id)
    resp = await client.get(
        "/api/v1/incidents",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_get_incident(client: AsyncClient, admin_token: str, test_org: Organization, db: AsyncSession):
    inc = await incident_crud.create(db, obj_in=IncidentCreate(
        organization_id=test_org.id,
        title="Get Test Incident",
        severity=IncidentSeverity.low,
    ), created_by=test_org.id)
    resp = await client.get(
        f"/api/v1/incidents/{inc.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == str(inc.id)


@pytest.mark.asyncio
async def test_update_incident_severity(client: AsyncClient, admin_token: str, test_org: Organization, db: AsyncSession):
    inc = await incident_crud.create(db, obj_in=IncidentCreate(
        organization_id=test_org.id,
        title="Severity Change Test",
        severity=IncidentSeverity.low,
    ), created_by=test_org.id)
    resp = await client.patch(
        f"/api/v1/incidents/{inc.id}",
        json={"severity": "critical"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["severity"] == "critical"


@pytest.mark.asyncio
async def test_incident_status_transition(client: AsyncClient, admin_token: str, test_org: Organization, db: AsyncSession):
    inc = await incident_crud.create(db, obj_in=IncidentCreate(
        organization_id=test_org.id,
        title="Status Transition Test",
        severity=IncidentSeverity.medium,
    ), created_by=test_org.id)
    resp = await client.post(
        f"/api/v1/incidents/{inc.id}/status",
        json={"status": "investigating", "rationale": "Starting investigation"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "investigating"


@pytest.mark.asyncio
async def test_invalid_status_transition(client: AsyncClient, admin_token: str, test_org: Organization, db: AsyncSession):
    inc = await incident_crud.create(db, obj_in=IncidentCreate(
        organization_id=test_org.id,
        title="Invalid Transition Test",
        severity=IncidentSeverity.medium,
    ), created_by=test_org.id)
    # Cannot go from open directly to resolved
    resp = await client.post(
        f"/api/v1/incidents/{inc.id}/status",
        json={"status": "resolved"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_incident_not_found(client: AsyncClient, admin_token: str):
    import uuid
    fake_id = uuid.uuid4()
    resp = await client.get(
        f"/api/v1/incidents/{fake_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_unauthenticated_cannot_list_incidents(client: AsyncClient):
    resp = await client.get("/api/v1/incidents")
    assert resp.status_code == 401
