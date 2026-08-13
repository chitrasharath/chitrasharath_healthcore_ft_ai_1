"""Readability metrics with auto NLTK punkt bootstrap + graceful degrade."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_PUNKT_READY = False


def _ensure_punkt() -> bool:
    """Ensure NLTK punkt tokenizers exist; download once if missing."""
    global _PUNKT_READY
    if _PUNKT_READY:
        return True
    try:
        import nltk

        try:
            nltk.data.find("tokenizers/punkt")
        except LookupError:
            logger.info("NLTK punkt missing — downloading")
            nltk.download("punkt", quiet=True)
            nltk.download("punkt_tab", quiet=True)
        _PUNKT_READY = True
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("NLTK punkt bootstrap failed: %s", type(exc).__name__)
        return False


def compute_readability(markdown: str) -> dict[str, Any]:
    text = (markdown or "").strip()
    if not text:
        return {"status": "unavailable", "reason": "empty_text"}

    _ensure_punkt()

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

        # Library needs ~100 words for FK; treat as unavailable so evaluator soft-passes
        if metrics.get("flesch_kincaid_grade") is None:
            err = metrics.get("flesch_kincaid_grade_error") or ""
            if "100 words" in err.lower() or "words required" in err.lower():
                metrics["status"] = "unavailable"
                metrics["reason"] = "insufficient_text"
        return metrics
    except Exception as exc:  # noqa: BLE001 — do not fail the job
        # One retry after forced download (cold start / empty cache)
        if type(exc).__name__ == "LookupError" and _ensure_punkt():
            try:
                from readability import Readability

                r = Readability(text)
                grade = float(r.flesch_kincaid().score)
                ease = float(r.flesch().score)
                return {
                    "status": "ok",
                    "flesch_kincaid_grade": grade,
                    "flesch_reading_ease": ease,
                }
            except Exception as retry_exc:  # noqa: BLE001
                logger.warning(
                    "readability unavailable after punkt retry: %s",
                    type(retry_exc).__name__,
                )
                return {"status": "unavailable", "reason": type(retry_exc).__name__}
        logger.warning("readability unavailable: %s", type(exc).__name__)
        return {"status": "unavailable", "reason": type(exc).__name__}
