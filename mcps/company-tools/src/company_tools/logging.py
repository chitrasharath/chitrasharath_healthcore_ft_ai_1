from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from typing import Any

from company_tools.redact import redact_pii

logger = logging.getLogger("company_tools.invocation")


class InvocationLogger:
    """Emit exactly one structured JSON log line per tool call."""

    def __init__(
        self,
        *,
        tool: str,
        subject: str | None,
        client_id: str | None,
        input_summary: dict[str, Any],
    ) -> None:
        self.tool = tool
        self.subject = subject
        self.client_id = client_id
        self.input_summary = _sanitize_summary(input_summary)
        self.result = "success"
        self.error_code: str | None = None
        self._start = time.perf_counter()
        self._emitted = False

    def fail(self, error_code: str) -> None:
        self.result = "error"
        self.error_code = error_code

    def emit(self) -> None:
        if self._emitted:
            return
        self._emitted = True
        duration_ms = int((time.perf_counter() - self._start) * 1000)
        logger.info(
            json.dumps(
                {
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "subject": self.subject,
                    "client_id": self.client_id,
                    "tool": self.tool,
                    "input_summary": self.input_summary,
                    "result": self.result,
                    "error_code": self.error_code,
                    "duration_ms": duration_ms,
                },
                default=str,
                separators=(",", ":"),
            )
        )


def _sanitize_summary(summary: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in summary.items():
        if key in {"description", "title"} and isinstance(value, str):
            out[key] = redact_pii(value)
        elif key.lower() in {"token", "authorization", "password", "secret"}:
            continue
        else:
            out[key] = value
    return out


def with_invocation_log(
    *,
    tool: str,
    subject: str | None,
    client_id: str | None,
    input_summary: dict[str, Any],
    fn: Callable[[InvocationLogger], dict[str, Any]],
) -> dict[str, Any]:
    inv = InvocationLogger(
        tool=tool,
        subject=subject,
        client_id=client_id,
        input_summary=input_summary,
    )
    try:
        payload = fn(inv)
        if not payload.get("ok", True) and payload.get("error_code"):
            inv.fail(str(payload["error_code"]))
        return payload
    except Exception:
        inv.fail("UPSTREAM_ERROR")
        raise
    finally:
        inv.emit()
