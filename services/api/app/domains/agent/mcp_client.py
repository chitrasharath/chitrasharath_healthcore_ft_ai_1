"""LangGraph ↔ company-tools MCP client (langchain-mcp-adapters)."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

DOWNSTREAM_AUTH_HEADER = "X-Downstream-Authorization"

_token_cache: dict[str, Any] = {"access_token": None, "expires_at": 0.0}


def _fetch_keycloak_token() -> str:
    """client_credentials token for MCP Authorization (cached until near expiry)."""
    now = time.time()
    cached = _token_cache.get("access_token")
    expires_at = float(_token_cache.get("expires_at") or 0)
    if cached and now < expires_at - 30:
        return str(cached)

    data = {
        "grant_type": "client_credentials",
        "client_id": settings.keycloak_client_id,
        "client_secret": settings.keycloak_client_secret,
        "scope": "incidents:read incidents:write inventory:read",
    }
    with httpx.Client(timeout=10.0) as client:
        response = client.post(settings.keycloak_token_url, data=data)
        response.raise_for_status()
        payload = response.json()
    token = payload["access_token"]
    expires_in = int(payload.get("expires_in") or 300)
    _token_cache["access_token"] = token
    _token_cache["expires_at"] = now + expires_in
    return str(token)


def build_mcp_headers(*, auth_token: str | None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {_fetch_keycloak_token()}"}
    if auth_token:
        headers[DOWNSTREAM_AUTH_HEADER] = f"Bearer {auth_token}"
    return headers


async def _ainvoke_tool(
    tool_name: str,
    arguments: dict[str, Any],
    *,
    auth_token: str | None,
) -> Any:
    from langchain_mcp_adapters.client import MultiServerMCPClient

    client = MultiServerMCPClient(
        {
            "company-tools": {
                "url": settings.mcp_company_tools_url,
                "transport": "streamable_http",
                "headers": build_mcp_headers(auth_token=auth_token),
            }
        }
    )
    tools = await client.get_tools(server_name="company-tools")
    tool = next((t for t in tools if t.name == tool_name), None)
    if tool is None:
        raise RuntimeError(f"MCP tool not found: {tool_name}")
    return await tool.ainvoke(arguments)


def _run_coro(coro: Any) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    # Already in an event loop (e.g. nested) — run in a fresh thread.
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


def _parse_tool_payload(raw: Any) -> dict[str, Any]:
    """Normalize langchain-mcp-adapters / MCP tool return shapes to a dict."""
    if isinstance(raw, dict):
        # Prefer structuredContent when adapters nest it
        structured = raw.get("structuredContent")
        if isinstance(structured, dict):
            return structured
        if "ok" in raw or "error_code" in raw:
            return raw
        # Single text content block shaped as dict
        if raw.get("type") == "text" and isinstance(raw.get("text"), str):
            return _parse_tool_payload(raw["text"])
        return raw
    if isinstance(raw, list):
        # langchain StructuredTool often returns [{"type":"text","text":"{...json...}"}]
        for item in raw:
            parsed = _parse_tool_payload(item)
            if isinstance(parsed, dict) and (
                "ok" in parsed or "error_code" in parsed or "incident" in parsed
                or "products" in parsed or "matched" in parsed
            ):
                return parsed
        if raw:
            return _parse_tool_payload(raw[0])
        return {"ok": False, "error_code": "UPSTREAM_ERROR", "error_message": "empty tool result"}
    if isinstance(raw, str):
        import json

        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {"ok": False, "error_code": "UPSTREAM_ERROR", "error_message": raw}
    return {"ok": False, "error_code": "UPSTREAM_ERROR", "error_message": str(raw)}


def _map_error_code(code: str | None) -> str | None:
    if not code:
        return None
    mapping = {
        "NOT_FOUND": "not_found",
        "UPSTREAM_TIMEOUT": "timeout",
        "AUTH_MISSING_TOKEN": "unauthenticated",
        "AUTH_INVALID_TOKEN": "unauthenticated",
        "AUTH_INSUFFICIENT_SCOPE": "forbidden",
        "VALIDATION_ERROR": "validation",
        "UPSTREAM_ERROR": "transport",
        "INVENTORY_WRITE_FORBIDDEN": "forbidden",
    }
    return mapping.get(code, code.lower())


def run_incident_via_mcp(
    *,
    action: str = "get",
    ticket_id: int | None = None,
    status: str | None = None,
    title: str | None = None,
    description: str | None = None,
    category: str | None = None,
    origin: str | None = None,
    branch: str | None = None,
    auth_token: str | None,
) -> dict[str, Any]:
    """Call manage_incident_ticket; never raises into the graph."""
    args: dict[str, Any] = {"action": action}
    if ticket_id is not None:
        args["ticket_id"] = ticket_id
    if status is not None:
        args["status"] = status
    if title is not None:
        args["title"] = title
    if description is not None:
        args["description"] = description
    if category is not None:
        args["category"] = category
    if origin is not None:
        args["origin"] = origin
    if branch is not None:
        args["branch"] = branch

    try:
        raw = _run_coro(
            _ainvoke_tool(
                "manage_incident_ticket", args, auth_token=auth_token
            )
        )
        payload = _parse_tool_payload(raw)
        if not payload.get("ok"):
            return {
                "source": "incident_tool",
                "ok": False,
                "incident": None,
                "incidents": [],
                "error": _map_error_code(payload.get("error_code")) or "transport",
                "empty": False,
            }
        incident = payload.get("incident")
        empty = not bool(incident)
        return {
            "source": "incident_tool",
            "ok": True,
            "incident": incident,
            "incidents": [],
            "error": None,
            "empty": empty,
        }
    except Exception as exc:
        logger.warning("Incident MCP call failed (%s)", exc)
        return {
            "source": "incident_tool",
            "ok": False,
            "incident": None,
            "incidents": [],
            "error": "transport",
            "empty": False,
        }


def run_inventory_via_mcp(
    *,
    name_hint: str | None = None,
    product_id: int | None = None,
    auth_token: str | None,
) -> dict[str, Any]:
    """Call query_inventory; never raises into the graph."""
    args: dict[str, Any] = {}
    if name_hint is not None:
        args["name_hint"] = name_hint
    if product_id is not None:
        args["product_id"] = product_id

    try:
        raw = _run_coro(
            _ainvoke_tool("query_inventory", args, auth_token=auth_token)
        )
        payload = _parse_tool_payload(raw)
        if not payload.get("ok"):
            return {
                "source": "inventory_tool",
                "ok": False,
                "products": [],
                "matched": [],
                "error": _map_error_code(payload.get("error_code")) or "transport",
                "empty": False,
            }
        products = list(payload.get("products") or [])
        matched = list(payload.get("matched") or [])
        empty = (not products) or (bool(name_hint) and not matched)
        return {
            "source": "inventory_tool",
            "ok": True,
            "products": products,
            "matched": matched,
            "error": None,
            "empty": empty,
        }
    except Exception as exc:
        logger.warning("Inventory MCP call failed (%s)", exc)
        return {
            "source": "inventory_tool",
            "ok": False,
            "products": [],
            "matched": [],
            "error": "transport",
            "empty": False,
        }
