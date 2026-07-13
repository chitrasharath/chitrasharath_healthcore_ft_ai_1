from __future__ import annotations

import time
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any, TypeVar

_TTL_SECONDS = 60
_store: dict[tuple[str, str], tuple[float, dict[str, Any]]] = {}

T = TypeVar("T")


def report_cache_key(start_date: datetime, end_date: datetime) -> tuple[str, str]:
    start = start_date.astimezone(timezone.utc).isoformat()
    end = end_date.astimezone(timezone.utc).isoformat()
    return (start, end)


def get_cached_or_compute(
    key: tuple[str, str],
    compute: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    now = time.monotonic()
    cached = _store.get(key)
    if cached is not None:
        cached_at, payload = cached
        if now - cached_at < _TTL_SECONDS:
            return payload

    payload = compute()
    _store[key] = (now, payload)
    return payload


def clear_report_cache() -> None:
    _store.clear()
