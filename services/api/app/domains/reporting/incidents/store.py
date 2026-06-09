from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any


@dataclass
class StoredAnalysis:
    response: Any
    export_rows: list[dict[str, Any]]


class LastAnalysisStore:
    """Thread-safe in-memory store for the most recent analysis."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._current: StoredAnalysis | None = None

    def save(self, response: Any, export_rows: list[dict[str, Any]]) -> None:
        with self._lock:
            self._current = StoredAnalysis(response=response, export_rows=export_rows)

    def get(self) -> StoredAnalysis | None:
        with self._lock:
            return self._current


last_analysis_store = LastAnalysisStore()
