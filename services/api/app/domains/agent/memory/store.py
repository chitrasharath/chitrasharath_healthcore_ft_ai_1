"""Redis system-of-record + Qdrant semantic recall for agent memory."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Callable, Protocol
from uuid import NAMESPACE_URL, uuid5

from app.domains.agent.memory import config as mem_config
from app.domains.agent.memory.audit import append_audit
from app.domains.agent.memory.schemas import MemoryEntry, MemoryProposal, MemoryScope

logger = logging.getLogger(__name__)

EmbedFn = Callable[[str], list[float]]


class MemoryStore(Protocol):
    def read(
        self, scope: MemoryScope, query: str, *, k: int = 5
    ) -> list[MemoryEntry]: ...

    def write(self, scope: MemoryScope, entry: MemoryEntry) -> None: ...

    def list(self, scope: MemoryScope) -> list[MemoryEntry]: ...

    def delete(self, scope: MemoryScope, mem_id: str) -> None: ...

    def touch(self, scope: MemoryScope, mem_id: str) -> None: ...

    def save_pending(self, staff_id: str, proposal: MemoryProposal) -> None: ...

    def pop_pending(self, staff_id: str) -> MemoryProposal | None: ...


def _entry_key(clinic_id: str, staff_id: str, mem_id: str) -> str:
    return f"mem:entry:{clinic_id}:{staff_id}:{mem_id}"


def _index_key(clinic_id: str, staff_id: str) -> str:
    return f"mem:index:{clinic_id}:{staff_id}"


def _pending_key(staff_id: str) -> str:
    return f"mem:pending:{staff_id}"


def _qdrant_point_id(mem_id: str) -> str:
    """Qdrant requires UUID/int ids — derive stable UUID from mem_id."""
    return str(uuid5(NAMESPACE_URL, f"healthcore:agent_memory:{mem_id}"))


def _hash_to_entry(data: dict[str, Any], scope: MemoryScope) -> MemoryEntry | None:
    if not data or not data.get("id"):
        return None
    try:
        return MemoryEntry(
            id=str(data["id"]),
            scope=scope,
            type=data.get("type") or "semantic",  # type: ignore[arg-type]
            text=str(data.get("text") or ""),
            created_at=int(data.get("created_at") or 0),
            last_recalled_at=int(data.get("last_recalled_at") or 0),
            recall_count=int(data.get("recall_count") or 0),
            source_trace_id=data.get("source_trace_id") or None,
        )
    except Exception:
        logger.debug("Skipping malformed memory hash", exc_info=True)
        return None


class RedisQdrantMemoryStore:
    """Redis SoT + Qdrant recall index. Inject clients for tests."""

    def __init__(
        self,
        redis_client: Any,
        qdrant_client: Any,
        *,
        embed_fn: EmbedFn | None = None,
        collection: str | None = None,
    ) -> None:
        self._redis = redis_client
        self._qdrant = qdrant_client
        self._embed = embed_fn
        self._collection = collection or mem_config.qdrant_collection()
        self._collection_ready = False

    def _embed_text(self, text: str) -> list[float]:
        if self._embed is not None:
            return self._embed(text)
        from data.process.rag import embed

        return embed(text)

    def _ensure_collection(self, dim: int) -> None:
        if self._collection_ready:
            return
        ensure = getattr(self._qdrant, "ensure_collection", None)
        if callable(ensure):
            ensure(self._collection, dim)
            self._collection_ready = True
            return
        # Real QdrantClient path
        try:
            from qdrant_client.http import models as qmodels

            names = {c.name for c in self._qdrant.get_collections().collections}
            if self._collection not in names:
                self._qdrant.create_collection(
                    collection_name=self._collection,
                    vectors_config=qmodels.VectorParams(
                        size=dim, distance=qmodels.Distance.COSINE
                    ),
                )
            self._collection_ready = True
        except Exception:
            logger.exception("Failed to ensure Qdrant collection %s", self._collection)

    def read(
        self, scope: MemoryScope, query: str, *, k: int | None = None
    ) -> list[MemoryEntry]:
        """Recall top-k memories for scope.

        Latency path: Redis keyword ranking first (no embedding). Qdrant/embed
        only when Redis has entries but keyword overlap finds nothing.
        Never re-indexes on the request path.
        """
        scope = scope.normalized()
        limit = k if k is not None else mem_config.recall_k()

        # Empty scope → one cheap ZRANGE, no embed.
        existing = self.list(scope)
        if not existing:
            return []

        hits = self._redis_fallback_ids(scope, query, limit, entries=existing)
        # Semantic recall only when keywords miss but memories exist.
        if not hits:
            try:
                vector = self._embed_text(query)
                self._ensure_collection(len(vector))
                hits = self._search_qdrant(scope, vector, limit)
            except Exception:
                logger.exception("memory Qdrant recall failed")
                hits = []

        entries: list[MemoryEntry] = []
        for mid in hits:
            entry = self._hydrate(scope, mid)
            if entry is None:
                self._redis.zrem(_index_key(scope.clinic_id, scope.staff_id), mid)
                self._delete_qdrant(mid)
                continue
            entries.append(entry)
            try:
                self.touch(scope, mid)
            except Exception:
                logger.debug("touch failed for %s", mid, exc_info=True)
        return entries

    def _hydrate(self, scope: MemoryScope, mem_id: str) -> MemoryEntry | None:
        key = _entry_key(scope.clinic_id, scope.staff_id, mem_id)
        if not self._redis.exists(key):
            return None
        return _hash_to_entry(self._redis.hgetall(key), scope)

    def _redis_fallback_ids(
        self,
        scope: MemoryScope,
        query: str,
        limit: int,
        *,
        entries: list[MemoryEntry] | None = None,
    ) -> list[str]:
        """Rank Redis-scoped entries by keyword overlap (no embedding)."""
        rows = entries if entries is not None else self.list(scope)
        if not rows:
            return []
        q_tokens = {t for t in query.lower().split() if len(t) > 2}

        def score(entry: MemoryEntry) -> float:
            text = entry.text.lower()
            overlap = sum(1.0 for t in q_tokens if t in text)
            return overlap + (0.01 * entry.recall_count)

        ranked = sorted(rows, key=score, reverse=True)
        with_overlap = [e for e in ranked if score(e) >= 1.0]
        # Only return keyword hits — empty means caller may try Qdrant.
        return [e.id for e in with_overlap[:limit]]

    def _search_qdrant(
        self, scope: MemoryScope, vector: list[float], limit: int
    ) -> list[str]:
        """Use query_points (current client); keep search() for FakeQdrant tests."""
        try:
            from qdrant_client.http import models as qmodels

            query_filter = qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="clinic_id",
                        match=qmodels.MatchValue(value=scope.clinic_id),
                    ),
                    qmodels.FieldCondition(
                        key="staff_id",
                        match=qmodels.MatchValue(value=scope.staff_id),
                    ),
                ]
            )
            if callable(getattr(self._qdrant, "query_points", None)):
                response = self._qdrant.query_points(
                    collection_name=self._collection,
                    query=vector,
                    query_filter=query_filter,
                    limit=limit,
                    with_payload=True,
                )
                points = getattr(response, "points", None) or []
                ids: list[str] = []
                for hit in points:
                    payload = getattr(hit, "payload", None) or {}
                    mid = payload.get("mem_id") if isinstance(payload, dict) else None
                    if mid:
                        ids.append(str(mid))
                return ids

            search = getattr(self._qdrant, "search", None)
            if not callable(search):
                return []
            try:
                hits = search(
                    collection_name=self._collection,
                    query_vector=vector,
                    query_filter=query_filter,
                    limit=limit,
                )
            except TypeError:
                hits = search(
                    self._collection,
                    query_vector=vector,
                    query_filter={
                        "clinic_id": scope.clinic_id,
                        "staff_id": scope.staff_id,
                    },
                    limit=limit,
                )
            ids = []
            for hit in hits or []:
                payload = getattr(hit, "payload", None) or {}
                mid = payload.get("mem_id") if isinstance(payload, dict) else None
                if mid:
                    ids.append(str(mid))
            return ids
        except Exception:
            logger.exception("Qdrant memory search failed")
            return []

    def write(self, scope: MemoryScope, entry: MemoryEntry) -> None:
        scope = scope.normalized()
        entry = entry.model_copy(update={"scope": scope})
        key = _entry_key(scope.clinic_id, scope.staff_id, entry.id)
        mapping = {
            "id": entry.id,
            "clinic_id": scope.clinic_id,
            "staff_id": scope.staff_id,
            "type": entry.type,
            "text": entry.text,
            "created_at": str(entry.created_at),
            "last_recalled_at": str(entry.last_recalled_at),
            "recall_count": str(entry.recall_count),
            "source_trace_id": entry.source_trace_id or "",
        }
        pipe = self._redis.pipeline()
        pipe.hset(key, mapping=mapping)
        pipe.expire(key, mem_config.entry_ttl_seconds())
        pipe.zadd(
            _index_key(scope.clinic_id, scope.staff_id),
            {entry.id: entry.last_recalled_at},
        )
        pipe.execute()

        try:
            vector = self._embed_text(entry.text)
            self._ensure_collection(len(vector))
            self._upsert_qdrant(scope, entry, vector)
        except Exception:
            logger.exception(
                "Qdrant upsert failed for mem_id=%s — Redis is SoT; reconcile later",
                entry.id,
            )

    def _upsert_qdrant(
        self, scope: MemoryScope, entry: MemoryEntry, vector: list[float]
    ) -> None:
        payload = {
            "mem_id": entry.id,
            "clinic_id": scope.clinic_id,
            "staff_id": scope.staff_id,
            "type": entry.type,
        }
        upsert = getattr(self._qdrant, "upsert", None)
        if not callable(upsert):
            return
        try:
            from qdrant_client.http import models as qmodels

            upsert(
                collection_name=self._collection,
                points=[
                    qmodels.PointStruct(
                        id=_qdrant_point_id(entry.id),
                        vector=vector,
                        payload=payload,
                    )
                ],
            )
        except TypeError:
            # Fake double: accept simplified signature
            Point = type("P", (), {})
            p = Point()
            p.id = entry.id
            p.payload = payload
            p.vector = vector
            upsert(self._collection, points=[p])

    def list(self, scope: MemoryScope) -> list[MemoryEntry]:
        scope = scope.normalized()
        index = _index_key(scope.clinic_id, scope.staff_id)
        mem_ids = self._redis.zrevrange(index, 0, -1) or []
        entries: list[MemoryEntry] = []
        for mid in mem_ids:
            mid_s = mid.decode() if isinstance(mid, bytes) else str(mid)
            key = _entry_key(scope.clinic_id, scope.staff_id, mid_s)
            if not self._redis.exists(key):
                self._redis.zrem(index, mid_s)
                self._delete_qdrant(mid_s)
                continue
            entry = _hash_to_entry(self._redis.hgetall(key), scope)
            if entry is not None:
                entries.append(entry)
        return entries

    def delete(self, scope: MemoryScope, mem_id: str) -> None:
        scope = scope.normalized()
        key = _entry_key(scope.clinic_id, scope.staff_id, mem_id)
        self._redis.delete(key)
        self._redis.zrem(_index_key(scope.clinic_id, scope.staff_id), mem_id)
        self._delete_qdrant(mem_id)
        append_audit(
            self._redis,
            event="deleted",
            staff_id=scope.staff_id,
            clinic_id=scope.clinic_id,
            mem_id=mem_id,
        )

    def _delete_qdrant(self, mem_id: str) -> None:
        delete = getattr(self._qdrant, "delete", None)
        if not callable(delete):
            return
        try:
            from qdrant_client.http import models as qmodels

            delete(
                collection_name=self._collection,
                points_selector=qmodels.PointIdsList(
                    points=[_qdrant_point_id(mem_id)]
                ),
            )
        except Exception:
            try:
                delete(self._collection, points_selector=[mem_id])
            except Exception:
                logger.debug("Qdrant delete failed for %s", mem_id, exc_info=True)

    def touch(self, scope: MemoryScope, mem_id: str) -> None:
        scope = scope.normalized()
        key = _entry_key(scope.clinic_id, scope.staff_id, mem_id)
        if not self._redis.exists(key):
            return
        now = int(time.time())
        pipe = self._redis.pipeline()
        pipe.hincrby(key, "recall_count", 1)
        pipe.hset(key, "last_recalled_at", now)
        pipe.expire(key, mem_config.entry_ttl_seconds())
        pipe.zadd(_index_key(scope.clinic_id, scope.staff_id), {mem_id: now})
        pipe.execute()

    def save_pending(self, staff_id: str, proposal: MemoryProposal) -> None:
        sid = staff_id.strip().lower()
        payload = proposal.model_dump(mode="json")
        self._redis.set(
            _pending_key(sid),
            json.dumps(payload),
            ex=mem_config.pending_ttl_seconds(),
        )

    def pop_pending(self, staff_id: str) -> MemoryProposal | None:
        sid = staff_id.strip().lower()
        key = _pending_key(sid)
        raw = None
        if hasattr(self._redis, "getdel"):
            raw = self._redis.getdel(key)
        else:
            pipe = self._redis.pipeline()
            pipe.get(key)
            pipe.delete(key)
            raw, _ = pipe.execute()
        if not raw:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode()
        try:
            data = json.loads(raw)
            return MemoryProposal.model_validate(data)
        except Exception:
            logger.exception("Invalid pending proposal JSON for staff_id=%s", sid)
            return None


_store: RedisQdrantMemoryStore | None = None
_store_failed = False
_store_failed_at = 0.0
_REDIS_RETRY_SECONDS = 15.0


def get_memory_store() -> RedisQdrantMemoryStore | None:
    """Lazy singleton. Returns None when memory disabled or Redis unreachable."""
    global _store, _store_failed, _store_failed_at
    from app.core.config import settings

    if not settings.memory_enabled:
        return None
    if _store is not None:
        return _store
    if (
        _store_failed
        and (time.monotonic() - _store_failed_at) < _REDIS_RETRY_SECONDS
    ):
        return None
    try:
        import redis as redis_lib

        from data.process.rag import get_qdrant_client

        client = redis_lib.Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        client.ping()
        _store = RedisQdrantMemoryStore(
            redis_client=client,
            qdrant_client=get_qdrant_client(),
            collection=settings.memory_qdrant_collection,
        )
        _store_failed = False
        return _store
    except Exception as exc:
        first_failure = not _store_failed
        _store_failed = True
        _store_failed_at = time.monotonic()
        if first_failure:
            logger.warning(
                "Memory store unavailable — disabling until Redis is reachable (%s)",
                exc,
            )
        return None


def reset_memory_store_for_tests() -> None:
    global _store, _store_failed, _store_failed_at
    _store = None
    _store_failed = False
    _store_failed_at = 0.0
