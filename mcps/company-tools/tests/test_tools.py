from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from company_tools import errors
from company_tools.tools.incidents import manage_incident_ticket
from company_tools.tools.inventory import query_inventory


@pytest.fixture
def scopes_all(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "company_tools.tools.incidents.auth.token_scopes",
        lambda: ["incidents:read", "incidents:write", "inventory:read"],
    )
    monkeypatch.setattr(
        "company_tools.tools.inventory.auth.token_scopes",
        lambda: ["incidents:read", "incidents:write", "inventory:read"],
    )
    monkeypatch.setattr(
        "company_tools.tools.incidents.auth.token_subject", lambda: "coordinator"
    )
    monkeypatch.setattr(
        "company_tools.tools.inventory.auth.token_subject", lambda: "coordinator"
    )
    monkeypatch.setattr(
        "company_tools.tools.incidents.auth.token_client_id", lambda: "agent-support"
    )
    monkeypatch.setattr(
        "company_tools.tools.inventory.auth.token_client_id", lambda: "agent-support"
    )


@pytest.fixture
def scopes_readonly(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "company_tools.tools.incidents.auth.token_scopes",
        lambda: ["incidents:read", "inventory:read"],
    )
    monkeypatch.setattr(
        "company_tools.tools.incidents.auth.token_subject", lambda: "readonly"
    )
    monkeypatch.setattr(
        "company_tools.tools.incidents.auth.token_client_id", lambda: "agent-support"
    )


def test_inventory_write_shaped_rejected(scopes_all):
    result = query_inventory(name_hint="mask", quantity=5)
    assert result["ok"] is False
    assert result["error_code"] == errors.INVENTORY_WRITE_FORBIDDEN
    assert "read-only" in (result["error_message"] or "").lower()


def test_inventory_extra_field_rejected(scopes_all):
    result = query_inventory(delta=1)
    assert result["ok"] is False
    assert result["error_code"] == errors.INVENTORY_WRITE_FORBIDDEN


def test_incident_validation_error(scopes_all):
    result = manage_incident_ticket(action="get")
    assert result["ok"] is False
    assert result["error_code"] == errors.VALIDATION_ERROR


def test_incident_insufficient_scope_on_create(scopes_readonly):
    result = manage_incident_ticket(action="create", title="t", description="d")
    assert result["ok"] is False
    assert result["error_code"] == errors.AUTH_INSUFFICIENT_SCOPE


def test_incident_get_happy(scopes_all, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "company_tools.tools.incidents.resolve_downstream_token",
        lambda _req: "fastapi-jwt",
    )
    incident = {"id": 1, "status": "open", "title": "t"}
    monkeypatch.setattr(
        "company_tools.tools.incidents.request_json",
        lambda *a, **k: incident,
    )
    result = manage_incident_ticket(action="get", ticket_id=1)
    assert result["ok"] is True
    assert result["incident"]["status"] == "open"


def test_inventory_match(scopes_all, monkeypatch: pytest.MonkeyPatch, respx_mock=None):
    products = [
        {
            "id": 1,
            "name": "Surgical mask (pack of 50)",
            "sku": "MASK-50",
            "current_stock": 10,
        }
    ]
    monkeypatch.setattr(
        "company_tools.tools.inventory.resolve_downstream_token",
        lambda _req: None,
    )
    monkeypatch.setattr(
        "company_tools.tools.inventory.request_json",
        lambda *a, **k: products,
    )
    result = query_inventory(name_hint="surgical masks")
    assert result["ok"] is True
    assert len(result["matched"]) == 1
    assert result["matched"][0]["sku"] == "MASK-50"


def test_prm_route_shape():
    from company_tools.auth import protected_resource_metadata_route
    from company_tools.config import Settings

    settings = Settings(
        oidc_issuer="http://localhost:8080/realms/healthcore",
        oidc_audience="company-tools-mcp",
        oidc_resource="http://localhost:9000/mcp",
        incidents_api_base_url="http://localhost:8000",
        inventory_api_base_url="http://localhost:8000",
    )
    route = protected_resource_metadata_route(settings)
    assert route.path == "/.well-known/oauth-protected-resource"


def test_config_exit_78(monkeypatch: pytest.MonkeyPatch):
    from company_tools.config import Settings, require_config

    cfg = Settings(
        oidc_issuer="",
        oidc_audience="company-tools-mcp",
        oidc_resource="http://localhost:9000/mcp",
    )
    with pytest.raises(SystemExit) as exc:
        require_config(cfg)
    assert exc.value.code == 78
