from __future__ import annotations

from sqlmodel import Session, select

from app.domains.telemetry.models import TelemetryEventRow
from tests.telemetry_helpers import latest_row, sample_event


def test_mixed_batch_partial_acceptance(telemetry_client, telemetry_session) -> None:
    payload = {
        "events": [
            sample_event("supply_list_viewed", event_id="evt-valid", item_count=5),
            {"event_type": "broken", "properties": {}},
            sample_event(
                "supply_consumption_form_abandoned",
                event_id="evt-extra",
                clinic_id=1,
                had_supply_selected=True,
                had_quantity=False,
                supply_id=99,
                abandon_trigger="navigation",
            ),
        ],
    }

    response = telemetry_client.post("/api/v1/telemetry/events", json=payload)

    assert response.status_code == 200
    assert response.json() == {"received": 3, "stored": 1, "rejected": 2}

    with Session(telemetry_session) as session:
        rows = session.exec(select(TelemetryEventRow)).all()
    assert len(rows) == 1
    assert rows[0].event_type == "supply_list_viewed"
    assert rows[0].tags["item_count"] == 5


def test_abandon_supply_only_persists_tags(telemetry_client, telemetry_session) -> None:
    payload = {
        "events": [
            sample_event(
                "supply_consumption_form_abandoned",
                clinic_id=1,
                had_supply_selected=True,
                had_quantity=False,
                jurisdiction="us",
                abandon_trigger="navigation",
            ),
        ],
    }

    response = telemetry_client.post("/api/v1/telemetry/events", json=payload)

    assert response.status_code == 200
    assert response.json() == {"received": 1, "stored": 1, "rejected": 0}

    row = latest_row(telemetry_session, "supply_consumption_form_abandoned")
    assert row.level == "info"
    assert row.value is None
    assert row.tags["schemaVersion"] == "1.1.0"
    assert row.tags["had_supply_selected"] is True
    assert row.tags["jurisdiction"] == "us"


def test_abandon_quantity_only_without_jurisdiction(telemetry_client, telemetry_session) -> None:
    payload = {
        "events": [
            sample_event(
                "supply_consumption_form_abandoned",
                event_id="evt-qty",
                clinic_id=1,
                had_supply_selected=False,
                had_quantity=True,
                abandon_trigger="tab_hidden",
            ),
        ],
    }

    response = telemetry_client.post("/api/v1/telemetry/events", json=payload)

    assert response.status_code == 200
    assert response.json() == {"received": 1, "stored": 1, "rejected": 0}

    row = latest_row(telemetry_session, "supply_consumption_form_abandoned")
    assert row.tags["had_quantity"] is True
    assert "jurisdiction" not in row.tags


def test_incident_filter_applied_persists_dimensions(telemetry_client, telemetry_session) -> None:
    payload = {
        "events": [
            sample_event(
                "incident_list_filter_applied",
                filter_dimension="status",
                filter_value="open",
                active_filter_count=1,
            ),
        ],
    }

    response = telemetry_client.post("/api/v1/telemetry/events", json=payload)

    assert response.status_code == 200
    assert response.json() == {"received": 1, "stored": 1, "rejected": 0}

    row = latest_row(telemetry_session, "incident_list_filter_applied")
    assert row.level == "info"
    assert row.tags["filter_dimension"] == "status"
    assert row.tags["active_filter_count"] == 1


def test_consumption_created_sets_value_column(telemetry_client, telemetry_session) -> None:
    payload = {
        "events": [
            sample_event(
                "supply_consumption_created",
                supply_id=3,
                quantity=20,
                consumption_type="clinical_use",
                clinic_id=10,
                jurisdiction="uk",
            ),
        ],
    }

    response = telemetry_client.post("/api/v1/telemetry/events", json=payload)

    assert response.status_code == 200
    row = latest_row(telemetry_session, "supply_consumption_created")
    assert row.value == 20.0
    assert row.tags["consumption_type"] == "clinical_use"


def test_failed_event_level_warn(telemetry_client, telemetry_session) -> None:
    payload = {
        "events": [
            sample_event(
                "supply_consumption_failed",
                error_code="INSUFFICIENT_STOCK",
                supply_id=1,
                clinic_id=1,
                jurisdiction="us",
            ),
        ],
    }

    response = telemetry_client.post("/api/v1/telemetry/events", json=payload)

    assert response.status_code == 200
    row = latest_row(telemetry_session, "supply_consumption_failed")
    assert row.level == "warn"


def test_unknown_event_type_rejected(telemetry_client, telemetry_session) -> None:
    payload = {
        "events": [
            sample_event("not_a_real_event", foo="bar"),
        ],
    }

    response = telemetry_client.post("/api/v1/telemetry/events", json=payload)

    assert response.status_code == 200
    assert response.json() == {"received": 1, "stored": 0, "rejected": 1}


def test_empty_batch(telemetry_client) -> None:
    response = telemetry_client.post("/api/v1/telemetry/events", json={"events": []})
    assert response.status_code == 200
    assert response.json() == {"received": 0, "stored": 0, "rejected": 0}


def test_no_auth_required(telemetry_client) -> None:
    response = telemetry_client.post(
        "/api/v1/telemetry/events",
        json={"events": [sample_event("user_login_succeeded")]},
    )
    assert response.status_code == 200
