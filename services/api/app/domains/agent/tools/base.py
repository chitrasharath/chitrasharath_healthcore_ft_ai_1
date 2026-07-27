from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_MAX_RETRIES = 1
_RETRY_SLEEP_SECONDS = 0.05


def tool_timeout() -> httpx.Timeout:
    t = settings.tool_http_timeout_seconds
    return httpx.Timeout(t, connect=min(t, 3.0))


def api_url(path: str) -> str:
    return f"{settings.internal_api_base_url.rstrip('/')}{path}"


def request_with_retry(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
) -> httpx.Response:
    """GET/POST with one retry on timeout or HTTP 5xx (mirrors RAG _generate)."""
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            with httpx.Client(timeout=tool_timeout()) as client:
                response = client.request(
                    method, url, headers=headers, params=params
                )
            if response.status_code >= 500 and attempt < _MAX_RETRIES:
                logger.warning(
                    "Tool HTTP %s %s returned %s — retrying once",
                    method,
                    url,
                    response.status_code,
                )
                time.sleep(_RETRY_SLEEP_SECONDS)
                continue
            return response
        except httpx.TimeoutException as exc:
            last_exc = exc
            if attempt < _MAX_RETRIES:
                logger.warning("Tool HTTP timeout on %s %s — retrying once", method, url)
                time.sleep(_RETRY_SLEEP_SECONDS)
                continue
            raise
        except httpx.TransportError as exc:
            last_exc = exc
            raise
    assert last_exc is not None
    raise last_exc
