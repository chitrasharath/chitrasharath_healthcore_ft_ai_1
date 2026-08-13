from __future__ import annotations

import logging
from typing import Any

import httpx
from starlette.requests import Request

from company_tools.config import Settings, get_settings
from company_tools import errors

logger = logging.getLogger(__name__)

DOWNSTREAM_HEADER_DEFAULT = "X-Downstream-Authorization"


class DownstreamError(Exception):
    def __init__(self, code: str, message: str | None = None, status: int | None = None):
        self.code = code
        self.message = message or errors.message_for(code)
        self.status = status
        super().__init__(self.message)


def _timeout(settings: Settings) -> httpx.Timeout:
    t = settings.downstream_http_timeout_seconds
    return httpx.Timeout(t, connect=min(t, 3.0))


def resolve_downstream_token(request: Request | None, settings: Settings | None = None) -> str | None:
    """Prefer FastAPI JWT from X-Downstream-Authorization; never log the value."""
    cfg = settings or get_settings()
    header_name = cfg.downstream_auth_header
    if request is None:
        return None
    raw = request.headers.get(header_name) or request.headers.get(header_name.lower())
    if not raw:
        return None
    parts = raw.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip() or None
    return raw.strip() or None


def _auth_headers(token: str | None) -> dict[str, str]:
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def request_json(
    method: str,
    url: str,
    *,
    token: str | None,
    json_body: dict[str, Any] | None = None,
    settings: Settings | None = None,
) -> Any:
    cfg = settings or get_settings()
    try:
        with httpx.Client(timeout=_timeout(cfg)) as client:
            response = client.request(
                method,
                url,
                headers=_auth_headers(token),
                json=json_body,
            )
    except httpx.TimeoutException as exc:
        raise DownstreamError(errors.UPSTREAM_TIMEOUT) from exc
    except httpx.TransportError as exc:
        logger.warning("Downstream transport error on %s %s", method, url, exc_info=True)
        raise DownstreamError(errors.UPSTREAM_ERROR) from exc

    if response.status_code == 404:
        raise DownstreamError(errors.NOT_FOUND, status=404)
    if response.status_code >= 500:
        raise DownstreamError(
            errors.UPSTREAM_ERROR,
            message=errors.message_for(
                errors.UPSTREAM_ERROR, f"HTTP {response.status_code}."
            ),
            status=response.status_code,
        )
    if response.status_code < 200 or response.status_code >= 300:
        raise DownstreamError(
            errors.UPSTREAM_ERROR,
            message=errors.message_for(
                errors.UPSTREAM_ERROR, f"HTTP {response.status_code}."
            ),
            status=response.status_code,
        )
    if response.status_code == 204 or not response.content:
        return None
    return response.json()


def incidents_url(path: str, settings: Settings | None = None) -> str:
    base = (settings or get_settings()).incidents_api_base_url.rstrip("/")
    return f"{base}{path}"


def inventory_url(path: str, settings: Settings | None = None) -> str:
    base = (settings or get_settings()).inventory_api_base_url.rstrip("/")
    return f"{base}{path}"
