"""
Integration tests for the Wazuh ingest endpoint.
"""
import uuid
import pytest
from unittest.mock import patch
from httpx import AsyncClient

from app.models import Organization


SAMPLE_ALERT = {
    "id": "wazuh-test-001",
    "timestamp": "2024-01-15T08:32:11.000+0000",
    "rule": {
        "id": "100001",
        "level": 12,
        "description": "Test Wazuh alert",
        "groups": ["test"],
    },
    "agent": {"id": "001", "name": "WIN-WS-CAROL-01"},
    "data": {"test": True},
}


@pytest.mark.asyncio
async def test_ingest_without_secret_configured(client: AsyncClient, test_org: Organization):
    """When WAZUH_INGEST_SECRET is empty, endpoint returns 503."""
    resp = await client.post(
        f"/api/v1/wazuh/{test_org.id}/ingest",
        json=[SAMPLE_ALERT],
        headers={"X-Wazuh-Secret": "anything"},
    )
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_ingest_wrong_secret(client: AsyncClient, test_org: Organization):
    """Wrong secret returns 401."""
    with patch("app.api.v1.wazuh.settings") as mock_settings:
        mock_settings.wazuh_ingest_secret = "correct-secret"
        resp = await client.post(
            f"/api/v1/wazuh/{test_org.id}/ingest",
            json=[SAMPLE_ALERT],
            headers={"X-Wazuh-Secret": "wrong-secret"},
        )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_ingest_missing_secret_header(client: AsyncClient, test_org: Organization):
    """Missing header returns 401 when secret is configured."""
    with patch("app.api.v1.wazuh.settings") as mock_settings:
        mock_settings.wazuh_ingest_secret = "correct-secret"
        resp = await client.post(
            f"/api/v1/wazuh/{test_org.id}/ingest",
            json=[SAMPLE_ALERT],
        )
    assert resp.status_code in (401, 503)  # no header → dependency raises


@pytest.mark.asyncio
async def test_ingest_unknown_org(client: AsyncClient):
    """Unknown org_id returns 404."""
    fake_org = uuid.uuid4()
    with patch("app.api.v1.wazuh.settings") as mock_settings:
        mock_settings.wazuh_ingest_secret = "secret"
        resp = await client.post(
            f"/api/v1/wazuh/{fake_org}/ingest",
            json=[SAMPLE_ALERT],
            headers={"X-Wazuh-Secret": "secret"},
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_ingest_alerts_success(client: AsyncClient, test_org: Organization):
    """Valid batch with correct secret ingests alerts."""
    with patch("app.api.v1.wazuh.settings") as mock_settings:
        mock_settings.wazuh_ingest_secret = "test-secret"
        resp = await client.post(
            f"/api/v1/wazuh/{test_org.id}/ingest",
            json=[
                {**SAMPLE_ALERT, "id": f"wazuh-unique-{uuid.uuid4()}"},
            ],
            headers={"X-Wazuh-Secret": "test-secret"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["received"] == 1
    assert data["ingested"] == 1
    assert data["duplicates"] == 0


@pytest.mark.asyncio
async def test_ingest_deduplication(client: AsyncClient, test_org: Organization):
    """Sending the same alert twice counts the second as a duplicate."""
    alert_id = f"dedup-test-{uuid.uuid4()}"
    event = {**SAMPLE_ALERT, "id": alert_id}

    with patch("app.api.v1.wazuh.settings") as mock_settings:
        mock_settings.wazuh_ingest_secret = "test-secret"

        # First ingest
        r1 = await client.post(
            f"/api/v1/wazuh/{test_org.id}/ingest",
            json=[event],
            headers={"X-Wazuh-Secret": "test-secret"},
        )
        assert r1.status_code == 200
        assert r1.json()["ingested"] == 1

        # Second ingest — same wazuh_alert_id
        r2 = await client.post(
            f"/api/v1/wazuh/{test_org.id}/ingest",
            json=[event],
            headers={"X-Wazuh-Secret": "test-secret"},
        )
    assert r2.status_code == 200
    assert r2.json()["duplicates"] == 1
    assert r2.json()["ingested"] == 0


@pytest.mark.asyncio
async def test_ingest_empty_batch(client: AsyncClient, test_org: Organization):
    """Empty batch is accepted without error."""
    with patch("app.api.v1.wazuh.settings") as mock_settings:
        mock_settings.wazuh_ingest_secret = "test-secret"
        resp = await client.post(
            f"/api/v1/wazuh/{test_org.id}/ingest",
            json=[],
            headers={"X-Wazuh-Secret": "test-secret"},
        )
    assert resp.status_code == 200
    assert resp.json()["received"] == 0
    assert resp.json()["ingested"] == 0


@pytest.mark.asyncio
async def test_wazuh_status_unconfigured(client: AsyncClient, admin_token: str):
    """Status endpoint returns configured=False when WAZUH_URL is not set."""
    resp = await client.get(
        "/api/v1/wazuh/status",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["configured"] is False
    assert data["available"] is False


@pytest.mark.asyncio
async def test_wazuh_status_student_forbidden(client: AsyncClient, student_token: str):
    resp = await client.get(
        "/api/v1/wazuh/status",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_wazuh_agents_unconfigured(client: AsyncClient, admin_token: str):
    """Agent list returns 503 when Wazuh is not configured."""
    resp = await client.get(
        "/api/v1/wazuh/agents",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 503
