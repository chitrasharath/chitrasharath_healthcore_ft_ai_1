"""Shared LLM helper for RFP intake agents (httpx proxy, no new SDKs)."""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Synthesizer / drafting can exceed 60s on the proxy; allow headroom + retries.
_LLM_TIMEOUT = httpx.Timeout(120.0, connect=15.0)
_LLM_MAX_ATTEMPTS = 3
_LLM_RETRY_SLEEP_S = 1.5


class LlmConfigError(RuntimeError):
    pass


class LlmCallError(RuntimeError):
    pass


def parse_fenced_json(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            raise
        data = json.loads(text[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("expected JSON object")
    return data


def chat_json(
    system: str,
    user: str,
    *,
    temperature: float = 0.0,
    model: str | None = None,
) -> dict[str, Any]:
    from app.core.config import settings

    if not settings.llm_api_key:
        raise LlmConfigError("LLM_API_KEY unset")

    url = f"{settings.llm_base_url.rstrip('/')}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model or settings.generation_model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }

    last_exc: Exception | None = None
    response: httpx.Response | None = None
    for attempt in range(1, _LLM_MAX_ATTEMPTS + 1):
        try:
            with httpx.Client(timeout=_LLM_TIMEOUT) as client:
                response = client.post(url, headers=headers, json=payload)
            break
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last_exc = exc
            logger.warning(
                "LLM request %s on attempt %s/%s: %s",
                type(exc).__name__,
                attempt,
                _LLM_MAX_ATTEMPTS,
                exc,
            )
            if attempt < _LLM_MAX_ATTEMPTS:
                time.sleep(_LLM_RETRY_SLEEP_S * attempt)
            continue
    else:
        raise LlmCallError(
            f"LLM request failed after {_LLM_MAX_ATTEMPTS} attempts: {last_exc}"
        ) from last_exc

    assert response is not None
    if response.status_code < 200 or response.status_code >= 300:
        raise LlmCallError(f"LLM proxy {response.status_code}: {response.text[:200]}")
    body = response.json()
    choices = body.get("choices") or []
    if not choices:
        raise LlmCallError("LLM malformed: no choices")
    content = (choices[0].get("message") or {}).get("content")
    if not isinstance(content, str) or not content.strip():
        raise LlmCallError("LLM malformed: empty content")
    try:
        return parse_fenced_json(content)
    except (json.JSONDecodeError, ValueError) as exc:
        raise LlmCallError(f"LLM malformed JSON: {exc}") from exc
