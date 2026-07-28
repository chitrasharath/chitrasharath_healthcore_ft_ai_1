"""Structured logging + in-process per-session guardrail counters."""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Any

from app.domains.knowledge.pii import redact_pii

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_session_counts: dict[str, dict[str, int]] = {}
_global_counts: dict[str, int] = {
    "security": 0,
    "content": 0,
    "structural": 0,
    "redirects": 0,
}


def _empty_bucket() -> dict[str, int]:
    return {"security": 0, "content": 0, "structural": 0, "redirects": 0}


def reset_metrics() -> None:
    """Test helper — clear in-memory counters."""
    with _lock:
        _session_counts.clear()
        for key in _global_counts:
            _global_counts[key] = 0


def log_guardrail_event(
    *,
    trace_id: str,
    session: str,
    guardrail: str,
    failure_type: str,
    action: str,
    message_preview: str,
    preview_max_chars: int = 80,
) -> None:
    preview = redact_pii(message_preview) or ""
    preview = preview[:preview_max_chars]
    payload = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "trace_id": trace_id,
        "session": session,
        "guardrail": guardrail,
        "failure_type": failure_type,
        "action": action,
        "message_preview": preview,
    }
    logger.info("guardrail_event %s", payload)


def record_event(
    session: str,
    *,
    failure_type: str | None,
    action: str | None,
) -> None:
    if not failure_type and action != "redirect":
        return
    with _lock:
        bucket = _session_counts.setdefault(session, _empty_bucket())
        if failure_type in {"security", "content", "structural"}:
            bucket[failure_type] = bucket.get(failure_type, 0) + 1
            _global_counts[failure_type] = _global_counts.get(failure_type, 0) + 1
        if action == "redirect":
            bucket["redirects"] = bucket.get("redirects", 0) + 1
            _global_counts["redirects"] = _global_counts.get("redirects", 0) + 1


def get_metrics(session: str | None = None) -> dict[str, int]:
    with _lock:
        if session:
            return dict(_session_counts.get(session, _empty_bucket()))
        return dict(_global_counts)


def process_events(
    events: list[dict[str, Any]],
    *,
    trace_id: str,
    session: str,
    preview_max_chars: int = 80,
) -> None:
    for event in events:
        log_guardrail_event(
            trace_id=trace_id,
            session=session,
            guardrail=str(event.get("guardrail") or "unknown"),
            failure_type=str(event.get("failure_type") or ""),
            action=str(event.get("action") or ""),
            message_preview=str(event.get("message_preview") or ""),
            preview_max_chars=preview_max_chars,
        )
        record_event(
            session,
            failure_type=event.get("failure_type"),
            action=event.get("action"),
        )
