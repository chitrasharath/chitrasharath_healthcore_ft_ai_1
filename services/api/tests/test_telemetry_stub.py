from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient

from app.main import app

logger = logging.getLogger(__name__)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _sample_event(event_type: str, **properties: object) -> dict:
    return {
        "eventId": "evt-001",
        "timestamp": "2026-07-08T12:00:00Z",
        "sessionId": "sess-001",
        "userId": "42",
        "event_type": event_type,
        "schemaVersion": "1.1.0",
        "requestId": "req-001",
        "service": "backoffice",
        "properties": properties,
    }


def test_telemetry_batch_accepts_events_without_auth(client: TestClient) -> None:
    payload = {
        "events": [
            _sample_event("user_login_succeeded"),
            _sample_event(
                "incident_list_filter_applied",
                filter_dimension="status",
                filter_value="open",
                active_filter_count=1,
            ),
            _sample_event(
                "supply_consumption_form_abandoned",
                clinic_id=1,
                had_supply_selected=True,
                had_quantity=False,
                abandon_trigger="navigation",
            ),
        ],
    }

    response = client.post("/api/v1/telemetry/events", json=payload)

    assert response.status_code == 200
    assert response.json() == {"received": 3}


def test_telemetry_batch_tolerates_malformed_item(client: TestClient) -> None:
    payload = {
        "events": [
            _sample_event("supply_list_viewed", item_count=5),
            {"event_type": "broken", "properties": {}},
        ],
    }

    response = client.post("/api/v1/telemetry/events", json=payload)

    assert response.status_code == 200
    assert response.json() == {"received": 2}


def test_telemetry_empty_batch(client: TestClient) -> None:
    response = client.post("/api/v1/telemetry/events", json={"events": []})

    assert response.status_code == 200
    assert response.json() == {"received": 0}
