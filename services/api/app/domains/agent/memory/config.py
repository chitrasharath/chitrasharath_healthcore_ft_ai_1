"""Memory settings helpers (thresholds / TTLs from app Settings)."""

from __future__ import annotations

from app.core.config import settings


def entry_ttl_seconds() -> int:
    return int(settings.memory_entry_ttl_days) * 86400


def pending_ttl_seconds() -> int:
    return int(settings.memory_pending_ttl_minutes) * 60


def recall_k() -> int:
    return int(settings.memory_recall_k)


def max_entries_per_scope() -> int:
    return int(settings.memory_max_entries_per_scope)


def dedupe_threshold() -> float:
    return float(settings.memory_dedupe_threshold)


def low_relevance_days() -> int:
    return int(settings.memory_low_relevance_days)


def summarize_min_cluster() -> int:
    return int(settings.memory_summarize_min_cluster)


def qdrant_collection() -> str:
    return str(settings.memory_qdrant_collection)
