"""Wrap RAG / MCP tool text as untrusted data for compose."""

from __future__ import annotations

import json
import re
from typing import Any

from app.domains.agent.harness.patterns import INSTRUCTION_MARKERS

_SPOOF_TAG = re.compile(
    r"</?\s*untrusted_source\b[^>]*>",
    re.I,
)


def _strip_spoof_tags(text: str) -> str:
    return _SPOOF_TAG.sub("", text)


def sanitize_instruction_markers(text: str) -> str:
    """Neutralize embedded instruction markers so they are not obeyed."""
    out = text
    for pattern in INSTRUCTION_MARKERS:
        out = pattern.sub("[filtered_instruction]", out)
    return out


def wrap_rag_chunk(chunk: str) -> str:
    cleaned = sanitize_instruction_markers(_strip_spoof_tags(chunk or ""))
    return (
        '<untrusted_source name="rag">\n'
        f"{cleaned}\n"
        "</untrusted_source>"
    )


def wrap_tool_json(label: str, payload: Any) -> str:
    raw = json.dumps(payload, default=str, indent=2)
    cleaned = sanitize_instruction_markers(_strip_spoof_tags(raw))
    safe_label = label if label in {"incident_tool", "inventory_tool"} else "tool"
    return (
        f'<untrusted_source name="{safe_label}">\n'
        f"{cleaned}\n"
        "</untrusted_source>"
    )
