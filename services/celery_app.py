"""Celery application for HealthCore async tasks (worker + Flower)."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

# Bootstrap: services/api (app.*) and repo root (data.*) — mirror data/pipelines/pipeline.py
_REPO_ROOT = Path(__file__).resolve().parents[1]
_API_ROOT = _REPO_ROOT / "services" / "api"
for _path in (_API_ROOT, _REPO_ROOT):
    path_str = str(_path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from celery import Celery

_DEFAULT_BROKER = "redis://redis:6379/0"


def _broker_url() -> str:
    return os.environ.get("REDIS_URL", _DEFAULT_BROKER).strip() or _DEFAULT_BROKER


def _result_backend(broker: str) -> str:
    """Use Redis logical DB 1 for results when broker ends with /0 (or any /N)."""
    parts = urlsplit(broker)
    path = parts.path or "/0"
    # path like "/0" or "/0/..." — take first segment as DB index
    segments = [s for s in path.split("/") if s != ""]
    if segments and segments[0].isdigit():
        segments[0] = "1"
    else:
        segments = ["1"]
    new_path = "/" + "/".join(segments)
    return urlunsplit((parts.scheme, parts.netloc, new_path, parts.query, parts.fragment))


BROKER_URL = _broker_url()
RESULT_BACKEND = _result_backend(BROKER_URL)

celery_app = Celery(
    "healthcore",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=["services.tasks"],
)

celery_app.conf.update(
    task_track_started=True,
    result_expires=3600,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
