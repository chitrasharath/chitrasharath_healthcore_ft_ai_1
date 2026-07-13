from __future__ import annotations

from fastapi.testclient import TestClient

from tests.telemetry_helpers import sample_event


def test_telemetry_batch_accepts_events_without_auth(telemetry_client: TestClient) -> None:
    payload = {
        "events": [
            sample_event("user_login_succeeded"),
            sample_event(
                "incident_list_filter_applied",
                event_id="evt-filter",
                filter_dimension="status",
                filter_value="open",
                active_filter_count=1,
            ),
            sample_event(
                "supply_consumption_form_abandoned",
                event_id="evt-abandon",
                clinic_id=1,
                had_supply_selected=True,
                had_quantity=False,
                abandon_trigger="navigation",
            ),
        ],
    }

    response = telemetry_client.post("/api/v1/telemetry/events", json=payload)

    assert response.status_code == 200
    assert response.json() == {"received": 3, "stored": 3, "rejected": 0}


def test_telemetry_batch_tolerates_malformed_item(telemetry_client: TestClient) -> None:
    payload = {
        "events": [
            sample_event("supply_list_viewed", item_count=5),
            {"event_type": "broken", "properties": {}},
        ],
    }

    response = telemetry_client.post("/api/v1/telemetry/events", json=payload)

    assert response.status_code == 200
    assert response.json() == {"received": 2, "stored": 1, "rejected": 1}


def test_telemetry_empty_batch(telemetry_client: TestClient) -> None:
    response = telemetry_client.post("/api/v1/telemetry/events", json={"events": []})

    assert response.status_code == 200
    assert response.json() == {"received": 0, "stored": 0, "rejected": 0}
