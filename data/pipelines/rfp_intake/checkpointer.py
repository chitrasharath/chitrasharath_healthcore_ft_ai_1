"""Postgres checkpointer factory for RFP approval graph (Phase 3)."""

from __future__ import annotations

import logging
from typing import Any

from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)

_postgres_saver: Any = None
_pool: Any = None
_setup_done = False


class CheckpointerError(RuntimeError):
    """Raised when a durable Postgres checkpoint cannot be established."""


def thread_config(ticket_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": str(ticket_id)}}


def _normalize_conn_string(url: str) -> str:
    conn = url.strip()
    for prefix in ("postgresql+psycopg2://", "postgresql+psycopg://"):
        if conn.startswith(prefix):
            return "postgresql://" + conn[len(prefix) :]
    return conn


def get_checkpointer(*, use_memory: bool = False):
    """Return PostgresSaver when DATABASE_URL is set.

    Unit tests pass ``use_memory=True`` for an isolated in-memory saver.
    Empty DATABASE_URL or a Postgres setup/connect failure raises — never
    silently degrade to MemorySaver (that would lose interrupts on restart).
    """
    global _postgres_saver, _pool, _setup_done
    if use_memory:
        return MemorySaver()

    from app.core.config import settings

    url = (settings.database_url or "").strip()
    if not url:
        raise CheckpointerError(
            "DATABASE_URL is not set — refusing in-memory approval checkpoints. "
            "Pass use_memory=True for unit tests."
        )

    if _postgres_saver is not None:
        return _postgres_saver

    from langgraph.checkpoint.postgres import PostgresSaver
    from psycopg.rows import dict_row
    from psycopg_pool import ConnectionPool

    conn_string = _normalize_conn_string(url)
    try:
        # prepare_threshold=None disables server-side prepared statements.
        # Required with Supabase/PgBouncer and ConnectionPool — otherwise
        # concurrent checkpointer writes raise DuplicatePreparedStatement (_pg3_*).
        _pool = ConnectionPool(
            conninfo=conn_string,
            max_size=5,
            kwargs={
                "autocommit": True,
                "prepare_threshold": None,
                "row_factory": dict_row,
            },
        )
        saver = PostgresSaver(_pool)
        if not _setup_done:
            saver.setup()
            _setup_done = True
            logger.info("Postgres checkpointer setup complete")
        _postgres_saver = saver
        # Invalidate any compiled graph that may hold a prior saver instance
        try:
            import data.pipelines.rfp_intake.approval_graph as ag

            ag._compiled = None
        except Exception:
            pass
        return _postgres_saver
    except Exception as exc:
        logger.exception(
            "Postgres checkpointer failed — refusing MemorySaver fallback"
        )
        raise CheckpointerError(
            "Postgres checkpointer failed — approval interrupts require a durable "
            "checkpoint. MemorySaver is test-only (use_memory=True)."
        ) from exc
