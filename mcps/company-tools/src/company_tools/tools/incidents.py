from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from company_tools import auth, errors
from company_tools.downstream import (
    DownstreamError,
    incidents_url,
    request_json,
    resolve_downstream_token,
)
from company_tools.logging import with_invocation_log
from company_tools.request_context import get_current_request


class ManageIncidentInput(BaseModel):
    action: Literal["create", "update_status", "get"]
    ticket_id: int | None = None
    status: str | None = None
    title: str | None = None
    description: str | None = None
    category: str | None = None
    origin: str | None = None
    branch: str | None = None

    @model_validator(mode="after")
    def validate_action_fields(self) -> ManageIncidentInput:
        if self.action == "update_status":
            if self.ticket_id is None or not self.status:
                raise ValueError(
                    "update_status requires ticket_id and status"
                )
        if self.action == "get" and self.ticket_id is None:
            raise ValueError("get requires ticket_id")
        return self


class IncidentToolOutput(BaseModel):
    ok: bool
    incident: dict[str, Any] | None = None
    error_code: str | None = None
    error_message: str | None = None


def _err(code: str, detail: str | None = None) -> dict[str, Any]:
    return {
        "ok": False,
        "incident": None,
        "error_code": code,
        "error_message": errors.message_for(code, detail),
    }


def manage_incident_ticket(**kwargs: Any) -> dict[str, Any]:
    summary = {
        "action": kwargs.get("action"),
        "ticket_id": kwargs.get("ticket_id"),
        "status": kwargs.get("status"),
        "title": kwargs.get("title"),
    }
    return with_invocation_log(
        tool="manage_incident_ticket",
        subject=auth.token_subject(),
        client_id=auth.token_client_id(),
        input_summary=summary,
        fn=lambda inv: _run_incident(kwargs, inv),
    )


def _run_incident(kwargs: dict[str, Any], inv: Any) -> dict[str, Any]:
    try:
        inp = ManageIncidentInput.model_validate(kwargs)
    except Exception as exc:
        return _err(errors.VALIDATION_ERROR, str(exc))

    if inp.action == "get":
        scope_err = auth.require_scopes("incidents:read")
    else:
        scope_err = auth.require_scopes("incidents:write")
    if scope_err:
        return {
            **scope_err,
            "incident": None,
        }

    token = resolve_downstream_token(get_current_request())
    if not token:
        return _err(
            errors.AUTH_MISSING_TOKEN,
            "Pass FastAPI JWT via X-Downstream-Authorization for incident API calls.",
        )

    try:
        if inp.action == "create":
            body = {
                k: v
                for k, v in {
                    "title": inp.title,
                    "description": inp.description,
                    "category": inp.category,
                    "origin": inp.origin,
                    "branch": inp.branch,
                }.items()
                if v is not None
            }
            data = request_json(
                "POST",
                incidents_url("/api/v1/incidents"),
                token=token,
                json_body=body,
            )
            return {"ok": True, "incident": data, "error_code": None, "error_message": None}

        if inp.action == "update_status":
            data = request_json(
                "PATCH",
                incidents_url(f"/api/v1/incidents/{inp.ticket_id}/status"),
                token=token,
                json_body={"status": inp.status},
            )
            return {"ok": True, "incident": data, "error_code": None, "error_message": None}

        # get
        data = request_json(
            "GET",
            incidents_url(f"/api/v1/incidents/{inp.ticket_id}"),
            token=token,
        )
        return {"ok": True, "incident": data, "error_code": None, "error_message": None}
    except DownstreamError as exc:
        return _err(exc.code, exc.message if exc.code == errors.UPSTREAM_ERROR else None)


def register_incident_tools(mcp: Any) -> None:
    @mcp.tool(
        name="manage_incident_ticket",
        description=(
            "Create, update status, or get an incident ticket in the HealthCore "
            "Incident Manager. Requires a valid OAuth access token with the "
            "appropriate incidents scope."
        ),
    )
    def _tool(
        action: Literal["create", "update_status", "get"],
        ticket_id: int | None = None,
        status: str | None = None,
        title: str | None = None,
        description: str | None = None,
        category: str | None = None,
        origin: str | None = None,
        branch: str | None = None,
    ) -> dict[str, Any]:
        return manage_incident_ticket(
            action=action,
            ticket_id=ticket_id,
            status=status,
            title=title,
            description=description,
            category=category,
            origin=origin,
            branch=branch,
        )
