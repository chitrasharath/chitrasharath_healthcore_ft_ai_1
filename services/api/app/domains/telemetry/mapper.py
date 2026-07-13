from __future__ import annotations

from typing import Any

from app.domains.telemetry.models import TelemetryEventRow
from app.domains.telemetry.schemas import TelemetryEvent

ALLOWED_SCHEMA_VERSIONS = frozenset({"1.1.0"})

EVENT_PROPERTY_ALLOWLIST: dict[str, frozenset[str]] = {
    "supply_delivery_created": frozenset({"supply_id", "quantity", "clinic_id", "jurisdiction"}),
    "supply_consumption_created": frozenset(
        {"supply_id", "quantity", "consumption_type", "clinic_id", "jurisdiction"},
    ),
    "supply_consumption_failed": frozenset({"error_code", "supply_id", "clinic_id", "jurisdiction"}),
    "supply_consumption_form_abandoned": frozenset(
        {"clinic_id", "had_supply_selected", "had_quantity", "jurisdiction", "abandon_trigger"},
    ),
    "supply_list_viewed": frozenset({"item_count"}),
    "orders_list_viewed": frozenset({"item_count"}),
    "incident_list_filter_applied": frozenset(
        {"filter_dimension", "filter_value", "active_filter_count"},
    ),
    "user_login_succeeded": frozenset({"jurisdiction"}),
    "user_login_failed": frozenset({"reason"}),
    "session_expired": frozenset(),
    "product_created": frozenset({"supply_id", "category", "jurisdiction"}),
}


def properties_are_allowlisted(event: TelemetryEvent) -> bool:
    allowed = EVENT_PROPERTY_ALLOWLIST.get(event.event_type)
    if allowed is None:
        return False
    if event.schemaVersion not in ALLOWED_SCHEMA_VERSIONS:
        return False
    return set(event.properties.keys()) <= allowed


def derive_level(event_type: str) -> str:
    if event_type.endswith("_failed") or event_type == "session_expired":
        return "warn"
    return "info"


def derive_value(event_type: str, properties: dict[str, Any]) -> float | None:
    if event_type not in {"supply_delivery_created", "supply_consumption_created"}:
        return None
    quantity = properties.get("quantity")
    if quantity is None:
        return None
    return float(quantity)


def build_tags(event: TelemetryEvent) -> dict[str, Any]:
    return {
        "eventId": event.eventId,
        "sessionId": event.sessionId,
        "userId": event.userId,
        "schemaVersion": event.schemaVersion,
        "requestId": event.requestId,
        **event.properties,
    }


def map_event_to_row(event: TelemetryEvent) -> TelemetryEventRow:
    return TelemetryEventRow(
        timestamp=event.timestamp,
        service=event.service,
        event_type=event.event_type,
        level=derive_level(event.event_type),
        value=derive_value(event.event_type, event.properties),
        message=None,
        tags=build_tags(event),
    )
