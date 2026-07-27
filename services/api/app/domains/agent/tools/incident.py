from __future__ import annotations

import logging
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field

from app.domains.agent.tools.base import api_url, request_with_retry

logger = logging.getLogger(__name__)


class IncidentToolInput(BaseModel):
    incident_id: int | None = None
    status: str | None = None
    origin: str | None = None
    branch: str | None = None
    category: str | None = None


class IncidentToolResult(BaseModel):
    source: Literal["incident_tool"] = "incident_tool"
    ok: bool
    incident: dict[str, Any] | None = None
    incidents: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None
    empty: bool = False


def run_incident_tool(
    inp: IncidentToolInput, *, auth_token: str | None
) -> IncidentToolResult:
    """Call incident HTTP API. Never raises into the graph."""
    if not auth_token:
        return IncidentToolResult(ok=False, error="unauthenticated")

    headers = {"Authorization": f"Bearer {auth_token}"}
    try:
        if inp.incident_id is not None:
            url = api_url(f"/api/v1/incidents/{inp.incident_id}")
            response = request_with_retry("GET", url, headers=headers)
            if response.status_code == 404:
                return IncidentToolResult(ok=False, error="not_found")
            if response.status_code < 200 or response.status_code >= 300:
                return IncidentToolResult(
                    ok=False, error=f"http_{response.status_code}"
                )
            data = response.json()
            if not data:
                return IncidentToolResult(ok=True, empty=True)
            return IncidentToolResult(ok=True, incident=data)

        params: dict[str, str] = {}
        if inp.status:
            params["status"] = inp.status
        if inp.origin:
            params["origin"] = inp.origin
        if inp.branch:
            params["branch"] = inp.branch
        if inp.category:
            params["category"] = inp.category
        url = api_url("/api/v1/incidents")
        response = request_with_retry(
            "GET", url, headers=headers, params=params or None
        )
        if response.status_code < 200 or response.status_code >= 300:
            return IncidentToolResult(
                ok=False, error=f"http_{response.status_code}"
            )
        rows = response.json()
        if not isinstance(rows, list):
            return IncidentToolResult(ok=False, error="transport")
        if not rows:
            return IncidentToolResult(ok=True, empty=True, incidents=[])
        return IncidentToolResult(ok=True, incidents=rows)
    except httpx.TimeoutException:
        return IncidentToolResult(ok=False, error="timeout")
    except httpx.TransportError:
        logger.warning("Incident tool transport error", exc_info=True)
        return IncidentToolResult(ok=False, error="transport")
    except Exception:
        logger.warning("Incident tool unexpected error", exc_info=True)
        return IncidentToolResult(ok=False, error="transport")
