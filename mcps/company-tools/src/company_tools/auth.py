"""MCP Auth wiring via mcpauth (not FastMCP built-in auth).

Installed mcpauth 0.1.1 uses AuthServerConfig mode (no ResourceServerConfig yet).
We still serve RFC 9728 Protected Resource Metadata ourselves and validate JWTs
via mcpauth bearer middleware against Keycloak JWKS.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

from mcpauth import MCPAuth
from mcpauth.config import AuthServerType
from mcpauth.exceptions import MCPAuthAuthServerException
from mcpauth.utils import fetch_server_config
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from company_tools.config import Settings, get_settings, require_config
from company_tools import errors

logger = logging.getLogger(__name__)

mcp_auth: MCPAuth | None = None


def init_auth(settings: Settings | None = None) -> MCPAuth:
    """Discover OIDC issuer / JWKS. Exit 69 if unreachable; 78 if config missing."""
    global mcp_auth
    cfg = require_config(settings)
    try:
        auth_server_config = fetch_server_config(cfg.oidc_issuer, AuthServerType.OIDC)
    except Exception as exc:
        print(
            f"Unavailable (exit 69): cannot reach OIDC issuer / JWKS at "
            f"{cfg.oidc_issuer!r}: {exc}",
            file=sys.stderr,
        )
        sys.exit(errors.EX_UNAVAILABLE)
    try:
        mcp_auth = MCPAuth(server=auth_server_config)
    except MCPAuthAuthServerException as exc:
        print(f"Unavailable (exit 69): invalid auth server config: {exc}", file=sys.stderr)
        sys.exit(errors.EX_UNAVAILABLE)
    return mcp_auth


def get_mcp_auth() -> MCPAuth:
    if mcp_auth is None:
        raise RuntimeError("Auth not initialized — call init_auth() first")
    return mcp_auth


def bearer_middleware_class(settings: Settings | None = None) -> type[BaseHTTPMiddleware]:
    cfg = settings or get_settings()
    auth = get_mcp_auth()
    return auth.bearer_auth_middleware(
        "jwt",
        audience=cfg.oidc_audience,
        required_scopes=cfg.required_scopes or None,
        show_error_details=True,
    )


class WwwAuthenticateMiddleware(BaseHTTPMiddleware):
    """Ensure 401 responses include WWW-Authenticate pointing at PRM (RFC 9728)."""

    def __init__(self, app: Any, *, resource: str) -> None:
        super().__init__(app)
        self.resource = resource.rstrip("/")
        self.prm_url = f"{self.resource.rsplit('/mcp', 1)[0]}/.well-known/oauth-protected-resource"
        if self.resource.endswith("/mcp"):
            base = self.resource[: -len("/mcp")] or self.resource
            self.prm_url = f"{base}/.well-known/oauth-protected-resource"
        else:
            self.prm_url = f"{self.resource}/.well-known/oauth-protected-resource"

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        if response.status_code in (401, 403):
            # Do not overwrite if already set.
            if "www-authenticate" not in {
                k.lower() for k in response.headers.keys()
            }:
                response.headers["WWW-Authenticate"] = (
                    f'Bearer resource_metadata="{self.prm_url}"'
                )
        return response


def protected_resource_metadata_route(settings: Settings | None = None) -> Route:
    cfg = settings or get_settings()

    async def endpoint(request: Request) -> Response:
        body = {
            "resource": cfg.oidc_resource,
            "authorization_servers": [cfg.oidc_issuer],
            "scopes_supported": [
                "incidents:read",
                "incidents:write",
                "inventory:read",
            ],
            "bearer_methods_supported": ["header"],
        }
        return JSONResponse(body)

    return Route(
        "/.well-known/oauth-protected-resource",
        endpoint,
        methods=["GET", "OPTIONS"],
    )


def token_scopes() -> list[str]:
    if mcp_auth is None:
        return []
    info = mcp_auth.auth_info
    if info is None:
        return []
    return list(info.scopes or [])


def token_subject() -> str | None:
    if mcp_auth is None:
        return None
    info = mcp_auth.auth_info
    return info.subject if info else None


def token_client_id() -> str | None:
    if mcp_auth is None:
        return None
    info = mcp_auth.auth_info
    return info.client_id if info else None


def require_scopes(*needed: str) -> dict[str, str] | None:
    """Return structured error dict if any scope is missing; else None."""
    have = set(token_scopes())
    missing = [s for s in needed if s not in have]
    if missing:
        return {
            "ok": False,
            "error_code": errors.AUTH_INSUFFICIENT_SCOPE,
            "error_message": errors.message_for(
                errors.AUTH_INSUFFICIENT_SCOPE,
                f"Missing: {', '.join(missing)}.",
            ),
        }
    return None
