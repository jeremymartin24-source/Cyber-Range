"""
Wazuh integration endpoints.

POST /wazuh/{org_id}/ingest   — receive forwarded Wazuh alerts (machine-to-machine)
GET  /wazuh/status            — report whether Wazuh is reachable (admin only)
GET  /wazuh/agents            — proxy Wazuh agent list to our Endpoint format (admin only)
"""

import secrets
import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.crud.alert import alert as alert_crud
from app.crud.organization import organization as org_crud
from app.database import get_db
from app.dependencies.auth import require_admin
from app.integrations.wazuh.client import WazuhUnavailable, wazuh_client
from app.integrations.wazuh.normalizer import normalize_batch
from app.models.endpoint import Endpoint
from app.models.user import User

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/wazuh", tags=["wazuh"])


# ── Helpers ────────────────────────────────────────────────────────────────────


def _require_ingest_secret(x_wazuh_secret: Annotated[str | None, Header()] = None) -> None:
    """
    Validate the shared ingest secret from the X-Wazuh-Secret header.
    If WAZUH_INGEST_SECRET is empty (not configured), reject all requests.
    """
    if not settings.wazuh_ingest_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Wazuh ingest secret is not configured on this server",
        )
    if not x_wazuh_secret or not secrets.compare_digest(
        x_wazuh_secret, settings.wazuh_ingest_secret
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Wazuh-Secret header",
        )


async def _agent_endpoint_map(db: AsyncSession, org_id: uuid.UUID) -> dict[str, uuid.UUID]:
    """Return {agent_name: endpoint_id} for endpoints belonging to this org."""
    result = await db.execute(
        select(Endpoint.hostname, Endpoint.id).where(Endpoint.organization_id == org_id)
    )
    return {row.hostname: row.id for row in result.all()}


# ── Schemas ────────────────────────────────────────────────────────────────────


class IngestResponse(BaseModel):
    received: int
    ingested: int
    duplicates: int


class WazuhStatusResponse(BaseModel):
    configured: bool
    available: bool
    url: str | None


# ── Routes ────────────────────────────────────────────────────────────────────


@router.post(
    "/{org_id}/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_200_OK,
)
async def ingest_alerts(
    org_id: uuid.UUID,
    events: list[dict],
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_ingest_secret),
):
    """
    Receive a batch of Wazuh alert events for a specific organization.

    Intended to be called by a Logstash/Filebeat pipeline or a custom
    Wazuh integration script, not by end users.

    Duplicate detection is based on ``wazuh_alert_id`` (the OpenSearch
    document ID).  Duplicates are silently skipped.
    """
    org = await org_crud.get(db, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    agent_map = await _agent_endpoint_map(db, org_id)
    normalized = normalize_batch(events, org_id=org_id, agent_endpoint_map=agent_map)

    ingested = 0
    duplicates = 0
    for alert_in in normalized:
        if alert_in.wazuh_alert_id:
            existing = await alert_crud.get_by_wazuh_id(db, alert_in.wazuh_alert_id)
            if existing:
                duplicates += 1
                continue
        await alert_crud.create(db, obj_in=alert_in)
        ingested += 1

    log.info(
        "wazuh_ingest_complete",
        org_id=str(org_id),
        received=len(events),
        ingested=ingested,
        duplicates=duplicates,
    )
    return IngestResponse(received=len(events), ingested=ingested, duplicates=duplicates)


@router.get("/status", response_model=WazuhStatusResponse)
async def wazuh_status(
    current_user: User = Depends(require_admin),
):
    """Report Wazuh connectivity status (admin only)."""
    available = await wazuh_client.is_available() if settings.wazuh_enabled else False
    return WazuhStatusResponse(
        configured=settings.wazuh_enabled,
        available=available,
        url=settings.wazuh_url,
    )


@router.get("/agents", response_model=list[dict])
async def list_wazuh_agents(
    current_user: User = Depends(require_admin),
):
    """
    Proxy the Wazuh agent list.  Useful for an admin to see which endpoints
    Wazuh knows about before importing them as Endpoints.
    """
    if not settings.wazuh_enabled:
        raise HTTPException(status_code=503, detail="Wazuh is not configured")
    try:
        return await wazuh_client.get_agents()
    except WazuhUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))
