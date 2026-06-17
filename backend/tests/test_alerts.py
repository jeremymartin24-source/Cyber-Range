from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import alert as alert_crud
from app.crud import incident as incident_crud
from app.models import Organization
from app.models.incident import IncidentSeverity
from app.schemas.alert import AlertCreate
from app.schemas.incident import IncidentCreate


@pytest.mark.asyncio
async def test_create_alert(client: AsyncClient, admin_token: str, test_org: Organization):
    resp = await client.post(
        "/api/v1/alerts",
        json={
            "organization_id": str(test_org.id),
            "rule_id": 5716,
            "rule_level": 5,
            "rule_description": "SSHD authentication failure",
            "rule_groups": ["syslog", "sshd", "authentication_failure"],
            "agent_id": "001",
            "agent_name": "bmg-web01",
            "raw_data": {"full_log": "sshd[12345]: Failed password for root"},
            "timestamp": datetime.now(UTC).isoformat(),
            "is_simulated": True,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["rule_level"] == 5
    assert data["is_simulated"] is True
    assert data["is_acknowledged"] is False


@pytest.mark.asyncio
async def test_list_alerts(
    client: AsyncClient, admin_token: str, test_org: Organization, db: AsyncSession
):
    await alert_crud.create(
        db,
        obj_in=AlertCreate(
            organization_id=test_org.id,
            rule_level=3,
            raw_data={},
            timestamp=datetime.now(UTC),
            is_simulated=True,
        ),
    )
    resp = await client.get(
        "/api/v1/alerts",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_acknowledge_alert(
    client: AsyncClient, admin_token: str, test_org: Organization, db: AsyncSession
):
    a = await alert_crud.create(
        db,
        obj_in=AlertCreate(
            organization_id=test_org.id,
            raw_data={"test": True},
            timestamp=datetime.now(UTC),
            is_simulated=True,
        ),
    )
    resp = await client.post(
        f"/api/v1/alerts/{a.id}/acknowledge",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_acknowledged"] is True
    assert data["acknowledged_by"] is not None


@pytest.mark.asyncio
async def test_acknowledge_already_acknowledged(
    client: AsyncClient, admin_token: str, test_org: Organization, db: AsyncSession
):
    a = await alert_crud.create(
        db,
        obj_in=AlertCreate(
            organization_id=test_org.id,
            raw_data={},
            timestamp=datetime.now(UTC),
            is_simulated=True,
        ),
    )
    await client.post(
        f"/api/v1/alerts/{a.id}/acknowledge",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    resp = await client.post(
        f"/api/v1/alerts/{a.id}/acknowledge",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_link_alert_to_incident(
    client: AsyncClient, admin_token: str, test_org: Organization, db: AsyncSession
):
    a = await alert_crud.create(
        db,
        obj_in=AlertCreate(
            organization_id=test_org.id,
            raw_data={},
            timestamp=datetime.now(UTC),
            is_simulated=True,
        ),
    )
    inc = await incident_crud.create(
        db,
        obj_in=IncidentCreate(
            organization_id=test_org.id,
            title="Link Test Incident",
            severity=IncidentSeverity.medium,
        ),
        created_by=test_org.id,
    )
    resp = await client.post(
        f"/api/v1/alerts/{a.id}/link",
        json={"incident_id": str(inc.id)},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert "linked" in resp.json()["message"]


@pytest.mark.asyncio
async def test_link_alert_twice(
    client: AsyncClient, admin_token: str, test_org: Organization, db: AsyncSession
):
    a = await alert_crud.create(
        db,
        obj_in=AlertCreate(
            organization_id=test_org.id,
            raw_data={},
            timestamp=datetime.now(UTC),
            is_simulated=True,
        ),
    )
    inc = await incident_crud.create(
        db,
        obj_in=IncidentCreate(
            organization_id=test_org.id,
            title="Duplicate Link Test",
            severity=IncidentSeverity.low,
        ),
        created_by=test_org.id,
    )
    await client.post(
        f"/api/v1/alerts/{a.id}/link",
        json={"incident_id": str(inc.id)},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    resp = await client.post(
        f"/api/v1/alerts/{a.id}/link",
        json={"incident_id": str(inc.id)},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_student_cannot_create_alert(
    client: AsyncClient, student_token: str, test_org: Organization
):
    resp = await client.post(
        "/api/v1/alerts",
        json={
            "organization_id": str(test_org.id),
            "raw_data": {},
            "timestamp": datetime.now(UTC).isoformat(),
        },
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp.status_code == 403
