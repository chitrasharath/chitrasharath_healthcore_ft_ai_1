# Agent Memory

Consent-gated long-term memory for the LangGraph support agent.

**Architecture:** Redis is the system of record (entries, pending consent, audit stream, TTL). Qdrant collection `agent_memory` is a rebuildable semantic recall index. Memory is injected as a bounded `[MEMORY]` block in the *user* message — never into the system prompt.

**Scope:** `clinic_id` + `staff_id` (JWT user id). Clinic ids are inventory catalog strings (`"1"`…`"9"`). Missing clinic → `"unassigned"`.

## Expiration / cleanup policy

| Mechanism | Default | Rationale |
|-----------|---------|-----------|
| Sliding Redis TTL | 90 days, refreshed on recall | Operational corrections go stale; GDPR storage-limitation |
| Zero-recall prune | `recall_count==0` and age > 30 days | Monthly ops cycle |
| Hard cap | 50 entries per scope | Forces consolidation; keeps top-k meaningful |

## Flow cycles

### Cycle A — approved

1. Login as `memory-north@example.com` / `memory-demo-1` (clinic `"2"` / Austin North).
2. Ask: *Heads up — referrals keep failing Monday mornings, tell people to retry after 11.*
3. Agent answers and may append a consent question; response includes `memory_proposal`.
4. Reply `approve` (or use Approve button) → *"Saved."* Entry written to Redis + Qdrant.
5. Later ask: *Any known issues with referrals?* → `memory_read` injects `[MEMORY]`; answer reflects it.

### Cycle B — not approved

- **B1 Reject:** proposal shown → `no, don't save that` / Reject → nothing written; audit `rejected`.
- **B2 Ignore:** proposal shown → new question (e.g. AXA coverage) → proposal disregarded; question answered; audit `dismissed_ignored`. Pending also expires in 30 minutes.
- **B3 PHI:** *Patient Johnson cancelled tomorrow, note that down.* → proposal never shown; refusal appended; audit `phi_rejected`.

## Local ops

```bash
docker compose up -d redis
# Redis URL for Compose API: redis://redis:6379/0
# Manual API: REDIS_URL=redis://localhost:6379/0

uv run seed   # creates demo memory users if missing
uv run python scripts/consolidate_agent_memory.py

# Suggested nightly cron (document only):
# 0 3 * * * cd /path/to/repo && uv run python scripts/consolidate_agent_memory.py
```

Kill-switch: `MEMORY_ENABLED=false`. Missing Redis → memory nodes pass through; agent still answers.

## Latency path

- **Read:** Redis keyword ranking first (no embed). Qdrant/embed only when keywords miss. No request-path reindex.
- **Propose:** Heuristic gate skips the propose LLM for lookups, chit-chat, and post-recall turns unless the user volunteers new ops knowledge.
- **Consolidate:** Over-cap on write is logged only; run `scripts/consolidate_agent_memory.py` for LLM/embed consolidation.

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/agent/query` | Optional `memory_proposal` on response |
| POST | `/api/v1/agent/memory/decision` | Button path: approve / edit / reject |
| GET | `/api/v1/agent/memory` | List caller-scoped memories |
| DELETE | `/api/v1/agent/memory/{id}` | Delete one entry (audit `deleted`) |

See `agent_memory_specs.md` Appendix A for Redis key schema.
