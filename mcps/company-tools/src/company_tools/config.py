from __future__ import annotations

import sys
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    oidc_issuer: str = ""
    oidc_audience: str = "company-tools-mcp"
    oidc_resource: str = "http://localhost:9000/mcp"
    mcp_required_scopes: str = "inventory:read"

    mcp_host: str = "0.0.0.0"
    mcp_port: int = 9000

    incidents_api_base_url: str = "http://localhost:8000"
    inventory_api_base_url: str = "http://localhost:8000"
    downstream_http_timeout_seconds: float = 5.0

    # Header the agent uses to pass the FastAPI JWT for downstream API calls.
    downstream_auth_header: str = "X-Downstream-Authorization"

    @property
    def required_scopes(self) -> list[str]:
        return [s for s in self.mcp_required_scopes.split() if s]


@lru_cache
def get_settings() -> Settings:
    return Settings()


def require_config(settings: Settings | None = None) -> Settings:
    """Validate required env; exit 78 (EX_CONFIG) on failure."""
    cfg = settings or get_settings()
    missing: list[str] = []
    if not cfg.oidc_issuer.strip():
        missing.append("OIDC_ISSUER")
    if not cfg.oidc_audience.strip():
        missing.append("OIDC_AUDIENCE")
    if not cfg.oidc_resource.strip():
        missing.append("OIDC_RESOURCE")
    if not cfg.incidents_api_base_url.strip():
        missing.append("INCIDENTS_API_BASE_URL")
    if not cfg.inventory_api_base_url.strip():
        missing.append("INVENTORY_API_BASE_URL")
    if missing:
        print(
            f"Config error (exit 78): missing required env: {', '.join(missing)}",
            file=sys.stderr,
        )
        sys.exit(78)
    return cfg
