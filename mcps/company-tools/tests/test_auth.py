from __future__ import annotations

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from company_tools.auth import WwwAuthenticateMiddleware, protected_resource_metadata_route
from company_tools.config import Settings


def _settings() -> Settings:
    return Settings(
        oidc_issuer="http://localhost:8080/realms/healthcore",
        oidc_audience="company-tools-mcp",
        oidc_resource="http://localhost:9000/mcp",
        incidents_api_base_url="http://localhost:8000",
        inventory_api_base_url="http://localhost:8000",
    )


def test_protected_resource_metadata_endpoint():
    settings = _settings()
    app = Starlette(routes=[protected_resource_metadata_route(settings)])
    client = TestClient(app)
    response = client.get("/.well-known/oauth-protected-resource")
    assert response.status_code == 200
    body = response.json()
    assert body["resource"] == settings.oidc_resource
    assert settings.oidc_issuer in body["authorization_servers"]
    assert "incidents:read" in body["scopes_supported"]


def test_www_authenticate_header_on_401():
    settings = _settings()

    async def deny(_request):
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    app = Starlette(
        routes=[Route("/mcp", deny, methods=["GET"])],
        middleware=[
            Middleware(
                WwwAuthenticateMiddleware, resource=settings.oidc_resource
            )
        ],
    )
    client = TestClient(app)
    response = client.get("/mcp")
    assert response.status_code == 401
    www = response.headers.get("www-authenticate", "")
    assert "Bearer" in www
    assert "oauth-protected-resource" in www
