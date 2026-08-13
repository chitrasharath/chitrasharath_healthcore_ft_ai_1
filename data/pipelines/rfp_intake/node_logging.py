"""Redacted per-node execution logging for the approval graph."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from data.pipelines.rfp_intake.phi import scan_and_redact


def _scrub_value(value: Any) -> Any:
    if isinstance(value, str):
        redacted, _, _ = scan_and_redact(value)
        return redacted
    if isinstance(value, dict):
        return {str(k): _scrub_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_scrub_value(v) for v in value]
    return value


def make_log_entry(
    *,
    agent: str,
    ticket_id: str,
    input_snapshot: Any = None,
    output_snapshot: Any = None,
    department_id: str | None = None,
    trigger_id: str | None = None,
) -> dict[str, Any]:
    return {
        "agent": agent,
        "ticket_id": ticket_id,
        "input": _scrub_value(input_snapshot),
        "output": _scrub_value(output_snapshot),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "department_id": department_id,
        "trigger_id": trigger_id,
    }
