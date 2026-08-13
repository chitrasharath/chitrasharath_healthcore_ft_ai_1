"""Postgres checkpointer factory for RFP approval graph (Phase 3)."""

from __future__ import annotations

import logging
from typing import Any

from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)

_postgres_saver: Any = None
_pool: Any = None
_setup_done = False
# Process-wide fallback so BackgroundTasks start + HTTP resume share one saver
_process_memory_saver: MemorySaver | None = None


def thread_config(ticket_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": str(ticket_id)}}


def _normalize_conn_string(url: str) -> str:
    conn = url.strip()
    for prefix in ("postgresql+psycopg2://", "postgresql+psycopg://"):
        if conn.startswith(prefix):
            return "postgresql://" + conn[len(prefix) :]
    return conn


def get_checkpointer(*, use_memory: bool = False):
    """Return PostgresSaver when DATABASE_URL is set; shared MemorySaver otherwise.

    Unit tests pass ``use_memory=True`` for an isolated in-memory saver.
    """
    global _postgres_saver, _pool, _setup_done, _process_memory_saver
    if use_memory:
        return MemorySaver()

    from app.core.config import settings

    url = (settings.database_url or "").strip()
    if not url:
        if _process_memory_saver is None:
            _process_memory_saver = MemorySaver()
            logger.warning(
                "DATABASE_URL empty — using process-wide MemorySaver for approval graph"
            )
        return _process_memory_saver

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
    except Exception:
        logger.exception(
            "Postgres checkpointer failed — falling back to process-wide MemorySaver"
        )
        if _process_memory_saver is None:
            _process_memory_saver = MemorySaver()
        return _process_memory_saver
