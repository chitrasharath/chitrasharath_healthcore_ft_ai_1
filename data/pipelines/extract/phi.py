from __future__ import annotations

import re
from typing import Any

import pandas as pd

from app.domains.telemetry.mapper import EVENT_PROPERTY_ALLOWLIST
from data.pipelines.config import ENVELOPE_TAG_KEYS

_EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
_DOB_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ALLOWED_TAG_KEYS = frozenset().union(*EVENT_PROPERTY_ALLOWLIST.values()) | ENVELOPE_TAG_KEYS


def _value_looks_like_phi(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip()
    if _EMAIL_RE.search(text):
        return True
    if _DOB_RE.match(text):
        return True
    if " " in text and text.replace(" ", "").isalpha() and text == text.title():
        return True
    return False


def scan_tags_for_phi(df: pd.DataFrame) -> tuple[bool, int]:
    """Return (tripped, quarantine_count). Fail closed on any disallowed key/PHI-like value."""
    if df.empty:
        return False, 0
    quarantined = 0
    tripped = False
    for tags in df["tags"].tolist():
        if not isinstance(tags, dict):
            quarantined += 1
            tripped = True
            continue
        extra = set(tags.keys()) - _ALLOWED_TAG_KEYS
        if extra:
            tripped = True
            quarantined += 1
            continue
        if any(_value_looks_like_phi(v) for v in tags.values()):
            tripped = True
            quarantined += 1
    return tripped, quarantined


def count_null_grain_rows(df: pd.DataFrame) -> int:
    if df.empty or "tags" not in df.columns:
        return 0
    count = 0
    for _, row in df.iterrows():
        tags = row.get("tags") or {}
        event_type = row.get("event_type")
        if event_type in {"supply_consumption_created", "supply_consumption_failed"}:
            if tags.get("clinic_id") is None or tags.get("jurisdiction") is None:
                count += 1
            elif event_type == "supply_consumption_failed" and tags.get("supply_id") is None:
                count += 1
    return count
