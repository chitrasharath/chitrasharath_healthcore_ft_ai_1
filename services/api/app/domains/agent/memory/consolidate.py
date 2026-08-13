"""Dedupe, summarize, and expire memories per scope."""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from app.domains.agent.memory import config as mem_config
from app.domains.agent.memory.audit import append_audit
from app.domains.agent.memory.phi import validate_no_phi
from app.domains.agent.memory.schemas import MemoryEntry, MemoryScope, new_mem_id
from app.domains.agent.memory.store import RedisQdrantMemoryStore

logger = logging.getLogger(__name__)


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _summarize_texts(texts: list[str]) -> str | None:
    from app.core.config import settings

    if not settings.llm_api_key:
        return texts[0] if texts else None
    url = f"{settings.llm_base_url.rstrip('/')}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }
    joined = "\n".join(f"- {t}" for t in texts)
    payload = {
        "model": settings.generation_model,
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Summarize these HealthCore operational memory notes into ONE "
                    "short PHI-free sentence. Invent nothing. Return plain text only."
                ),
            },
            {"role": "user", "content": joined},
        ],
    }
    try:
        with httpx.Client(timeout=httpx.Timeout(40.0, connect=5.0)) as client:
            response = client.post(url, headers=headers, json=payload)
        if response.status_code < 200 or response.status_code >= 300:
            return None
        content = (
            (response.json().get("choices") or [{}])[0]
            .get("message", {})
            .get("content")
        )
        if isinstance(content, str) and content.strip():
            return content.strip()
    except Exception:
        logger.warning("Consolidation summarize failed", exc_info=True)
    return None


def consolidate_scope(store: RedisQdrantMemoryStore, scope: MemoryScope) -> dict[str, Any]:
    """Run dedupe/summarize/expire for one scope. No-raise; returns stats."""
    scope = scope.normalized()
    lock_key = f"mem:lock:consolidate:{scope.clinic_id}:{scope.staff_id}"
    redis = store._redis
    acquired = redis.set(lock_key, "1", nx=True, ex=60)
    if not acquired:
        return {"skipped": True, "reason": "lock_held"}

    try:
        entries = store.list(scope)
        before = len(entries)
        now = int(time.time())
        low_days = mem_config.low_relevance_days()
        low_cutoff = now - low_days * 86400

        kept: list[MemoryEntry] = []
        for entry in entries:
            if entry.recall_count == 0 and entry.created_at < low_cutoff:
                store.delete(scope, entry.id)
                continue
            kept.append(entry)

        # Embed for clustering
        vectors: list[list[float]] = []
        for entry in kept:
            try:
                vectors.append(store._embed_text(entry.text))
            except Exception:
                vectors.append([])

        threshold = mem_config.dedupe_threshold()
        min_cluster = mem_config.summarize_min_cluster()
        used: set[int] = set()
        clusters: list[list[int]] = []
        for i in range(len(kept)):
            if i in used or not vectors[i]:
                continue
            cluster = [i]
            used.add(i)
            for j in range(i + 1, len(kept)):
                if j in used or not vectors[j]:
                    continue
                if _cosine(vectors[i], vectors[j]) >= threshold:
                    cluster.append(j)
                    used.add(j)
            clusters.append(cluster)

        for cluster in clusters:
            if len(cluster) < 2:
                continue
            members = [kept[i] for i in cluster]
            members.sort(
                key=lambda e: (e.recall_count, e.last_recalled_at), reverse=True
            )
            if len(cluster) >= min_cluster:
                summary = _summarize_texts([m.text for m in members])
                if not summary:
                    continue
                ok, reasons = validate_no_phi(summary)
                if not ok:
                    append_audit(
                        redis,
                        event="phi_rejected_consolidation",
                        staff_id=scope.staff_id,
                        clinic_id=scope.clinic_id,
                        reasons=",".join(reasons),
                        omit_preview=True,
                    )
                    continue
                for m in members:
                    store.delete(scope, m.id)
                now_ts = int(time.time())
                store.write(
                    scope,
                    MemoryEntry(
                        id=new_mem_id(),
                        scope=scope,
                        type=members[0].type,
                        text=summary,
                        created_at=now_ts,
                        last_recalled_at=now_ts,
                        recall_count=sum(m.recall_count for m in members),
                        source_trace_id=members[0].source_trace_id,
                    ),
                )
            else:
                # Collapse near-duplicates: keep best, sum recall
                keep = members[0]
                drop = members[1:]
                total_recall = sum(m.recall_count for m in members)
                for m in drop:
                    store.delete(scope, m.id)
                keep = keep.model_copy(update={"recall_count": total_recall})
                store.write(scope, keep)

        after = len(store.list(scope))
        append_audit(
            redis,
            event="consolidated",
            staff_id=scope.staff_id,
            clinic_id=scope.clinic_id,
            before=before,
            after=after,
        )
        return {"skipped": False, "before": before, "after": after}
    except Exception:
        logger.exception("Consolidation failed for %s/%s", scope.clinic_id, scope.staff_id)
        return {"skipped": True, "reason": "error"}
    finally:
        try:
            redis.delete(lock_key)
        except Exception:
            pass


def maybe_consolidate_after_write(
    store: RedisQdrantMemoryStore, scope: MemoryScope
) -> None:
    """Best-effort hard-cap check — never raises.

    Request path stays cheap: log when over cap and leave LLM/embed
    consolidation to ``scripts/consolidate_agent_memory.py``.
    """
    try:
        count = len(store.list(scope))
        if count > mem_config.max_entries_per_scope():
            logger.warning(
                "memory scope %s/%s over cap (%s); run consolidate script",
                scope.clinic_id,
                scope.staff_id,
                count,
            )
    except Exception:
        logger.exception("maybe_consolidate_after_write failed")
