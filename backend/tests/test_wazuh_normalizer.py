"""
Unit tests for the Wazuh event normalizer.
No DB, no HTTP calls — pure function tests.
"""

import uuid
from datetime import UTC

from app.integrations.wazuh.normalizer import _parse_timestamp, normalize_batch, normalize_event

ORG_ID = uuid.uuid4()

SAMPLE_EVENT = {
    "id": "abc123",
    "timestamp": "2024-01-15T08:32:11.000+0000",
    "rule": {
        "id": "100001",
        "level": 12,
        "description": "Malicious attachment executed via Outlook",
        "groups": ["phishing", "malware"],
    },
    "agent": {"id": "001", "name": "WIN-WS-CAROL-01", "ip": "10.0.0.10"},
    "data": {"event_id": 4688, "process_name": "powershell.exe"},
    "full_log": "Jan 15 08:32:11 WIN-WS-CAROL-01 WindowsEvent...",
    "decoder": {"name": "windows"},
}


def test_normalize_event_basic():
    alert = normalize_event(SAMPLE_EVENT, org_id=ORG_ID)
    assert alert.wazuh_alert_id == "abc123"
    assert alert.organization_id == ORG_ID
    assert alert.rule_id == 100001
    assert alert.rule_level == 12
    assert alert.rule_description == "Malicious attachment executed via Outlook"
    assert alert.rule_groups == ["phishing", "malware"]
    assert alert.agent_id == "001"
    assert alert.agent_name == "WIN-WS-CAROL-01"
    assert alert.is_simulated is False
    assert alert.endpoint_id is None


def test_normalize_event_with_endpoint_id():
    ep_id = uuid.uuid4()
    alert = normalize_event(SAMPLE_EVENT, org_id=ORG_ID, endpoint_id=ep_id)
    assert alert.endpoint_id == ep_id


def test_normalize_event_preserves_raw_data():
    alert = normalize_event(SAMPLE_EVENT, org_id=ORG_ID)
    assert alert.raw_data["data"]["process_name"] == "powershell.exe"
    assert "full_log" in alert.raw_data
    assert "decoder" in alert.raw_data


def test_normalize_event_rule_id_as_string():
    event = {
        **SAMPLE_EVENT,
        "rule": {"id": "99999", "level": 5, "description": "test", "groups": []},
    }
    alert = normalize_event(event, org_id=ORG_ID)
    assert alert.rule_id == 99999
    assert isinstance(alert.rule_id, int)


def test_normalize_event_rule_id_none():
    event = {**SAMPLE_EVENT, "rule": {"level": 5, "description": "no id"}}
    alert = normalize_event(event, org_id=ORG_ID)
    assert alert.rule_id is None


def test_normalize_event_missing_agent():
    event = {k: v for k, v in SAMPLE_EVENT.items() if k != "agent"}
    alert = normalize_event(event, org_id=ORG_ID)
    assert alert.agent_id is None
    assert alert.agent_name is None


def test_normalize_event_missing_timestamp():
    event = {k: v for k, v in SAMPLE_EVENT.items() if k != "timestamp"}
    alert = normalize_event(event, org_id=ORG_ID)
    assert alert.timestamp.tzinfo is not None


def test_normalize_event_z_suffix_timestamp():
    event = {**SAMPLE_EVENT, "timestamp": "2024-06-01T12:00:00.000Z"}
    alert = normalize_event(event, org_id=ORG_ID)
    assert alert.timestamp.tzinfo is not None
    assert alert.timestamp.year == 2024


def test_normalize_event_no_wazuh_id():
    event = {k: v for k, v in SAMPLE_EVENT.items() if k != "id"}
    alert = normalize_event(event, org_id=ORG_ID)
    assert alert.wazuh_alert_id is None


def test_normalize_batch_maps_endpoints():
    ep_id = uuid.uuid4()
    agent_map = {"WIN-WS-CAROL-01": ep_id}
    events = [SAMPLE_EVENT, {**SAMPLE_EVENT, "id": "xyz789", "agent": {"name": "unknown-host"}}]
    alerts = normalize_batch(events, org_id=ORG_ID, agent_endpoint_map=agent_map)
    assert len(alerts) == 2
    assert alerts[0].endpoint_id == ep_id
    assert alerts[1].endpoint_id is None


def test_normalize_batch_empty():
    assert normalize_batch([], org_id=ORG_ID) == []


def test_normalize_batch_no_agent_map():
    alerts = normalize_batch([SAMPLE_EVENT], org_id=ORG_ID)
    assert len(alerts) == 1
    assert alerts[0].endpoint_id is None


def test_parse_timestamp_utc_offset():
    dt = _parse_timestamp("2024-03-10T14:22:00.000+0000")
    assert dt.tzinfo is not None
    assert dt.year == 2024
    assert dt.hour == 14


def test_parse_timestamp_z_suffix():
    dt = _parse_timestamp("2024-03-10T14:22:00Z")
    assert dt.tzinfo is not None


def test_parse_timestamp_none():
    dt = _parse_timestamp(None)
    assert dt.tzinfo == UTC


def test_parse_timestamp_invalid():
    dt = _parse_timestamp("not-a-date")
    assert dt.tzinfo is not None
