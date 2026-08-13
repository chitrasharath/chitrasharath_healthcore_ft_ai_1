"""In-state trace helpers + optional LangSmith env wiring.

LangSmith exports runs automatically when LANGCHAIN_TRACING_V2=true and
LANGCHAIN_API_KEY are set. Missing key disables tracing; the graph still runs.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_PROJECT = "healthcore-agent"
_DEFAULT_ENDPOINT = "https://api.smith.langchain.com"


def configure_langsmith_env() -> None:
    """Echo LangSmith settings into the process env (no-op hard dependency)."""
    os.environ.setdefault("LANGCHAIN_PROJECT", _DEFAULT_PROJECT)
    os.environ.setdefault("LANGCHAIN_ENDPOINT", _DEFAULT_ENDPOINT)
    tracing = os.environ.get("LANGCHAIN_TRACING_V2", "").lower() in {"1", "true", "yes"}
    has_key = bool(os.environ.get("LANGCHAIN_API_KEY", "").strip())
    if tracing and not has_key:
        # Avoid hard failure — LangGraph runs without remote traces.
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        logger.debug("LangSmith tracing disabled: LANGCHAIN_API_KEY unset")


def trace_step(node: str, order: int, summary: str) -> dict[str, Any]:
    return {"node": node, "order": order, "output_summary": summary}


configure_langsmith_env()
