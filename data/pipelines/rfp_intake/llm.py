"""Shared LLM helper for RFP intake agents (httpx proxy, no new SDKs)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

logger = logging.getLogger(__name__)


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


def chat_json(system: str, user: str, *, temperature: float = 0.0) -> dict[str, Any]:
    from app.core.config import settings

    if not settings.llm_api_key:
        raise LlmConfigError("LLM_API_KEY unset")

    url = f"{settings.llm_base_url.rstrip('/')}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.generation_model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    with httpx.Client(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
        response = client.post(url, headers=headers, json=payload)
    if response.status_code < 200 or response.status_code >= 300:
        raise LlmCallError(f"LLM proxy {response.status_code}: {response.text[:200]}")
    body = response.json()
    choices = body.get("choices") or []
    if not choices:
        raise LlmCallError("LLM malformed: no choices")
    content = (choices[0].get("message") or {}).get("content")
    if not isinstance(content, str) or not content.strip():
        raise LlmCallError("LLM malformed: empty content")
    return parse_fenced_json(content)
