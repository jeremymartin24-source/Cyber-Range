"""
Convert raw Wazuh v4 alert events into AlertCreate objects.

Wazuh alert structure (abbreviated):
{
  "id": "<opensearch-doc-id>",
  "timestamp": "2024-01-15T08:32:11.123+0000",
  "rule": {"id": "100001", "level": 12, "description": "...", "groups": [...]},
  "agent": {"id": "001", "name": "WIN-WS-CAROL-01", "ip": "10.0.0.10"},
  "data": {...},
  "full_log": "..."
}
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.schemas.alert import AlertCreate


def _parse_timestamp(ts: str | None) -> datetime:
    if not ts:
        return datetime.now(timezone.utc)
    try:
        # Python 3.11 fromisoformat handles "+0000" offset notation
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return datetime.now(timezone.utc)


def _parse_rule_id(rule: dict) -> int | None:
    raw = rule.get("id")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def normalize_event(event: dict, *, org_id: uuid.UUID, endpoint_id: uuid.UUID | None = None) -> AlertCreate:
    """
    Convert a single Wazuh alert dict into an AlertCreate.

    ``endpoint_id`` may be supplied by the caller after matching
    ``event["agent"]["name"]`` against the Endpoint table.
    """
    rule = event.get("rule", {})
    agent = event.get("agent", {})

    raw_data: dict = {}
    if event.get("data"):
        raw_data["data"] = event["data"]
    if event.get("full_log"):
        raw_data["full_log"] = event["full_log"]
    if event.get("decoder"):
        raw_data["decoder"] = event["decoder"]

    return AlertCreate(
        organization_id=org_id,
        wazuh_alert_id=event.get("id"),
        rule_id=_parse_rule_id(rule),
        rule_level=rule.get("level"),
        rule_description=rule.get("description"),
        rule_groups=rule.get("groups", []),
        agent_id=agent.get("id"),
        agent_name=agent.get("name"),
        endpoint_id=endpoint_id,
        raw_data=raw_data,
        timestamp=_parse_timestamp(event.get("timestamp")),
        is_simulated=False,
    )


def normalize_batch(
    events: list[dict],
    *,
    org_id: uuid.UUID,
    agent_endpoint_map: dict[str, uuid.UUID] | None = None,
) -> list[AlertCreate]:
    """
    Normalize a list of Wazuh events.

    ``agent_endpoint_map`` maps agent name → Endpoint UUID for FK linkage.
    """
    agent_map = agent_endpoint_map or {}
    alerts: list[AlertCreate] = []
    for event in events:
        agent_name = event.get("agent", {}).get("name")
        endpoint_id = agent_map.get(agent_name) if agent_name else None
        alerts.append(normalize_event(event, org_id=org_id, endpoint_id=endpoint_id))
    return alerts
