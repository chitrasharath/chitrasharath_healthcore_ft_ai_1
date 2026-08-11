"""Readability metrics with graceful degrade when NLTK punkt is unavailable."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def compute_readability(markdown: str) -> dict[str, Any]:
    text = (markdown or "").strip()
    if not text:
        return {"status": "unavailable", "reason": "empty_text"}
    try:
        from readability import Readability

        r = Readability(text)
        metrics: dict[str, Any] = {"status": "ok"}
        for name, fn in (
            ("flesch_reading_ease", lambda: r.flesch().score),
            ("flesch_kincaid_grade", lambda: r.flesch_kincaid().score),
            ("smog", lambda: r.smog().score),
            ("gunning_fog", lambda: r.gunning_fog().score),
        ):
            try:
                metrics[name] = float(fn())
            except Exception as exc:  # noqa: BLE001 — per-metric soft fail
                metrics[name] = None
                metrics[f"{name}_error"] = str(exc)[:120]
        return metrics
    except Exception as exc:  # noqa: BLE001 — do not fail the job
        logger.warning("readability unavailable: %s", type(exc).__name__)
        return {"status": "unavailable", "reason": type(exc).__name__}
