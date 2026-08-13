"""Fail-loud Postgres checkpointer — MemorySaver only via use_memory=True."""

from __future__ import annotations

import pytest
from langgraph.checkpoint.memory import MemorySaver

from app.core.config import settings
from data.pipelines.rfp_intake.checkpointer import (
    CheckpointerError,
    get_checkpointer,
)


def _reset_factory() -> None:
    import data.pipelines.rfp_intake.checkpointer as cp

    cp._postgres_saver = None
    cp._pool = None
    cp._setup_done = False


def test_use_memory_returns_isolated_memory_saver() -> None:
    first = get_checkpointer(use_memory=True)
    second = get_checkpointer(use_memory=True)
    assert isinstance(first, MemorySaver)
    assert isinstance(second, MemorySaver)
    assert first is not second


def test_empty_database_url_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_factory()
    monkeypatch.setattr(settings, "database_url", "")
    with pytest.raises(CheckpointerError, match="DATABASE_URL is not set"):
        get_checkpointer()


def test_postgres_connect_failure_raises_not_memorysaver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_factory()
    monkeypatch.setattr(settings, "database_url", "postgresql://invalid.example/db")
    # Import with the real ConnectionPool first — patching beforehand breaks
    # LangGraph's ConnectionPool[...] type alias on import.
    import langgraph.checkpoint.postgres  # noqa: F401

    def _boom(*_args, **_kwargs):
        raise OSError("connection refused")

    monkeypatch.setattr("psycopg_pool.ConnectionPool", _boom)
    with pytest.raises(CheckpointerError, match="Postgres checkpointer failed"):
        get_checkpointer()
