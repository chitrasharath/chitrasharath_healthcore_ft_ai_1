# Spec — Agent Memory: consent-gated long-term memory for the RAG agent (continuation of `feature/agent_harness`)

> **Audience:** a coding agent adding long-term memory to the HealthCore LangGraph support agent.
> **Prerequisites:** Parts 1–4 implemented — RAG-on-LangGraph, incident/inventory tools, Company Tools MCP + migration, and the guardrail harness (`prompts/system.py`, `harness/`). The agent graph lives in `services/api/app/domains/agent/`.
> **Reference context:** `4GeeksAcademy/ai-engineering-syllabus` → `content/contexts/08-agent-engineering/memory/CONTEXT-healthcore.md`.
> **Branch:** cut a new feature branch **`feature/agent_memory`** off `feature/agent_harness`. Open the PR back into `feature/agent_harness`.

---

## 1. Project overview

The agent answers front-desk questions from RAG + live tools, behind a guardrail harness. It currently has **no memory** — it cannot recall recurring operational corrections ("the referral system fails on Monday mornings"), local protocol exceptions, or a staff member's presentation preferences. This part adds **long-term, operational memory** that is:

- **Explicitly read and written** through a `MemoryStore` interface — recalled memories are injected as a **bounded, labeled context block**, never dumped into the system prompt.
- **Self-evaluated** after each interaction: the agent asks itself (via an LLM **memory proposal**, reusing the existing classifier pattern) whether anything is worth remembering, and dismisses what isn't.
- **Consent-gated**: a surviving proposal is shown to the staff user with **approve / edit / reject** options; the reply is interpreted by **reusing the existing scope/route classifier** (no new HITL framework). Ignoring the question (typing a new question) **disregards** the proposal. Every proposal + decision is **logged**.
- **PHI-safe (HIPAA / UK GDPR)**: no patient identifier or PHI may ever enter memory. Every proposal is PHI-validated **before** being shown, and consolidation **re-validates** before writing.
- **Bounded**: a consolidation mechanism dedupes, summarizes, and expires entries so memory does not grow without limit.

### Memory type & scope (from the context)
- **Semantic** memory: recurring clinic protocols / incident patterns *without patient data*.
- **Procedural** memory: staff preferences for how operational info is presented.
- **Scope:** per-**clinic** and per-**staff**. **Not** episodic/patient-level. **Never** patient data.

---

## 2. Memory architecture — proposed choices + selection

The task requires proposing persistent-backend choices and selecting one.

| Option | What | Fit | Verdict |
|---|---|---|---|
| **A. Redis (KV) + Qdrant (vectors)** | Redis = system-of-record, audit log, pending-consent store (native **TTL** for expiration); Qdrant = semantic recall of memory entries | Fast reads, TTL gives cleanup "for free", vector recall keeps the read interface relevant as memory grows; Qdrant already in the stack | **SELECTED** |
| B. Redis only (KV/RediSearch) | Store + scoped lookup by tag; RediSearch for keyword/vector | One store, but weaker semantic recall than Qdrant unless RediSearch vector is configured | Fallback if Qdrant is off-limits |
| C. Postgres (SQLModel) | Structured memory + audit tables | Strong audit/transactions, but no native TTL decay; more schema work | Viable; heavier for this scope |
| D. Mem0 / LangMem / Letta(MemGPT) | Batteries-included memory framework | Fast to start, but a large dependency, its own store, and less control over the mandatory PHI validation | Not chosen (compliance control) |

### Selected architecture: **Redis (system-of-record + audit + pending consent) + Qdrant (semantic recall)**

- **Redis** (new infra — add a `redis` service to `docker-compose.yml` and the `redis` Python client):
  - **Memory entries** — `mem:entry:{clinic_id}:{staff_id}:{mem_id}` → Hash `{ id, clinic_id, staff_id, type, text, created_at, last_recalled_at, recall_count, source_trace_id }`. A per-scope index sorted set `mem:index:{clinic_id}:{staff_id}` (scored by `last_recalled_at`) for enumeration/consolidation. **TTL** on each entry key (default 90 days, refreshed on recall — §7).
  - **Pending consent** — `mem:pending:{staff_id}` → JSON of the awaiting proposal, **TTL 30 min** so an ignored proposal auto-expires (implements "disregard").
  - **Audit log** — Redis **Stream** `mem:audit` (append-only): every proposal, decision, PHI rejection, and consolidation event (§6, §8).
  - **Exact key schema, field lists, and commands: see Appendix A.**
- **Qdrant** — a **separate** collection `agent_memory` (do **not** mix with the RAG `company_knowledge_base` vectors). Each approved entry is embedded (reuse `settings.embedding_model` = `pplx-embed-v1`) with payload `{ mem_id, clinic_id, staff_id, type }`; read-time recall is a scoped similarity search (filter by `clinic_id`/`staff_id`). Deleting/expiring a Redis entry also removes its Qdrant point.

> Redis is the source of truth; Qdrant is a recall index rebuildable from Redis. On any inconsistency, Redis wins.

---

## 3. Tech stack (delta)

Unchanged base: Python ≥3.12, `uv`, FastAPI, LangGraph (`MemorySaver`), Qdrant, `httpx`, the guardrail harness. New in this part:

| Concern | Choice | Notes |
|---|---|---|
| Memory store / audit / pending consent | **Redis** (`redis>=5` async or sync client) | new `docker-compose` service `redis`; native TTL |
| Semantic recall | **Qdrant** (existing) | new collection `agent_memory`; reuse `embed()` |
| Proposal / consent / consolidation LLM | existing 4Geeks proxy, JSON output, temp 0 | **reuse the classifier pattern** from `nodes.py` / `harness/input_guards.py` |
| PHI validation | **reuse** `harness/input_guards.detect_phi` + `output_guards` PHI scan + `redact_pii` | mandatory pre-show and pre-consolidation |
| Scope identity | JWT `user_id` (staff) + user record `clinic_id` | add `clinic_id` to the TinyDB user schema/seed (§9) |

---

## 4. Explicit read/write interface (Requirement 1)

New subpackage `services/api/app/domains/agent/memory/`:
```
memory/
  __init__.py
  store.py          # MemoryStore protocol + RedisQdrantMemoryStore impl (read/write/list/delete/expire)
  schemas.py        # MemoryEntry, MemoryProposal, MemoryDecision, MemoryScope (Pydantic)
  proposal.py       # LLM self-eval → MemoryProposal (classifier-style JSON)
  consent.py        # consent-intent classifier (reuse route/scope classifier pattern)
  consolidate.py    # dedupe + summarize + expire (§7)
  phi.py            # validate_no_phi(text) -> (ok, reasons)  — wraps harness detect_phi + redact_pii
  audit.py          # append to Redis Stream mem_audit; never stores PHI
  config.py         # thresholds, TTLs, k (recall size), consolidation limits
```

**The interface is explicit — memory is never appended wholesale to the system prompt.** Read returns a **bounded top-k** (default `k=5`) scoped, relevance-ranked set that a node injects as a single labeled `[MEMORY]` block in the *user* message (isolated like other external content, §12):

```python
# memory/store.py
class MemoryScope(BaseModel):
    clinic_id: str
    staff_id: str

class MemoryEntry(BaseModel):
    id: str
    scope: MemoryScope
    type: Literal["semantic", "procedural"]
    text: str
    created_at: datetime
    last_recalled_at: datetime
    recall_count: int = 0

class MemoryStore(Protocol):
    def read(self, scope: MemoryScope, query: str, *, k: int = 5) -> list[MemoryEntry]: ...   # semantic recall, scoped
    def write(self, scope: MemoryScope, entry: MemoryEntry) -> None: ...                        # after consent + PHI ok
    def list(self, scope: MemoryScope) -> list[MemoryEntry]: ...
    def delete(self, scope: MemoryScope, mem_id: str) -> None: ...                              # also removes Qdrant point
    def touch(self, scope: MemoryScope, mem_id: str) -> None: ...                               # refresh TTL + recall stats
    def save_pending(self, staff_id: str, proposal: MemoryProposal) -> None: ...               # Redis TTL 30m
    def pop_pending(self, staff_id: str) -> MemoryProposal | None: ...
```

**Graph read node (`memory_read`):** after `input_guards` passes, call `store.read(scope, question)`; inject the returned entries as a `[MEMORY]` block into the compose context and `touch()` any recalled entries (updates `last_recalled_at`, refreshes TTL). If nothing recalled, no block. Recall is **read-only** and never blocks answering.

---

## 5. Self-evaluation — memory proposal (Requirement 2)

After the answer is composed (post `output_guards`), a **`memory_propose`** node asks the model whether anything is worth remembering — **reusing the classifier pattern** (a strict-JSON LLM call, temp 0, like `classify_node`):

```json
{
  "worth_remembering": true,
  "type": "semantic",
  "memory_text": "Referral submissions fail on Monday mornings; retry after 11am.",
  "scope_hint": "clinic",
  "reasoning": "Recurring operational correction, no patient data."
}
```

### 5.1 Criteria — worth remembering
- Recurring **operational corrections** per clinic (schedule changes, local protocols, admin exceptions by country).
- Known **incident patterns** *without patient data*.
- **Staff presentation preferences** (e.g., "always show stock as units, not cases").

### 5.2 Dismiss — not worth remembering (agent must self-dismiss)
The proposal node returns `worth_remembering: false` (no user prompt) for these. **Three concrete examples the spec requires:**
1. **One-off factual lookup** — *"What's the late-cancellation fee for Medicaid in the US?"* → answerable from RAG every time; the fact lives in the knowledge base, not memory. Dismiss.
2. **Conversation closing / chit-chat** — *"Thanks, that's all for now."* / *"Good morning!"* → no durable operational value. Dismiss.
3. **PHI / patient-specific request** — *"Patient Johnson cancelled tomorrow's appointment, note that down."* → contains a patient identifier. **Not merely dismissed — hard-rejected** by PHI validation (§6), logged, and the agent explains it cannot store patient information.

### 5.3 Mandatory PHI validation *before* showing (Requirement, from context)
Every proposal with `worth_remembering: true` passes `memory/phi.validate_no_phi(memory_text)` (wraps `harness/input_guards.detect_phi` + `redact_pii` + quasi-identifier check). **If PHI is detected → the proposal is rejected, never shown, logged as `phi_rejected`,** and the agent appends a short explanation. "Validating only at the initial proposal moment isn't enough" — consolidation re-validates too (§7).

---

## 6. Consent flow — approve / edit / reject (Requirement 3)

Reuses the **existing scope/route classifier** rather than any new HITL framework (per the locked decision, §14).

### 6.1 Ask
When a proposal survives PHI validation, `memory_propose` **appends a consent question** to the answer and stores the pending proposal in Redis (`save_pending`, TTL 30m):
> *"I noticed something worth remembering for this clinic: **"Referral submissions fail Monday mornings; retry after 11am."** May I save it? You can **approve**, **edit** (reply with the corrected text), or **reject**."*

The `AgentQueryResponse` also carries a structured `memory_proposal` object (id + text + options) so the frontend can render **Approve / Edit / Reject** buttons (§10). Free-text replies and button actions resolve to the same decisions.

### 6.2 Interpret the reply (reuse the classifier)
On the **next** `/agent/query` turn, a **`memory_consent_check`** node runs first (after `receive_question`): if `pop_pending(staff_id)` returns a proposal, classify the reply with a **consent-intent classifier** (same structured-JSON, temp-0 pattern as the route/scope classifiers):
```json
{"decision": "approve" | "edit" | "reject" | "new_question", "edited_text": "…|null"}
```
- **approve** → `validate_no_phi` again → `store.write(...)` → embed into Qdrant → confirm to user; log `approved`.
- **edit** → validate the edited text → write the edited version; log `edited`.
- **reject** → discard; log `rejected`.
- **new_question** → the user ignored the consent and asked something else → **disregard** the proposal (let audit note `dismissed_ignored`) and process the new question normally through the graph. (The 30-min TTL is the backstop if the user never returns.)

**Every proposal and decision is logged** to the `mem_audit` stream (§8), PHI-free.

### 6.3 Buttons path (optional, equivalent)
Approve/Edit/Reject buttons `POST /api/v1/agent/memory/decision { proposal_id, decision, edited_text? }` → same `consent` resolution + audit. Provided for UX; the classifier path is the primary/required one.

---

## 7. Consolidation, expiration & cleanup (Requirement 4)

`memory/consolidate.py` keeps memory bounded. Triggered when a scope exceeds `memory_max_entries_per_scope` (default 50) or on a nightly job (reuse the existing job runner if available; else a manual `uv run` script + a suggested schedule).

**Mechanism (per scope):**
1. **Dedupe** — cluster entries by embedding similarity (cosine ≥ `dedupe_threshold`, default 0.92); collapse near-duplicates, keeping the most-recalled/most-recent, summing `recall_count`.
2. **Summarize** — when a cluster has ≥ `summarize_min_cluster` (default 3) related entries, replace them with one LLM-summarized entry (temp 0).
3. **Discard low-relevance** — drop entries with `recall_count == 0` older than `low_relevance_days` (default 30) — never recalled, low value.
4. **Re-validate PHI** — `validate_no_phi` on every summarized/consolidated text **before writing**; a failure discards that consolidation and logs `phi_rejected_consolidation`.
5. Rebuild the affected Qdrant points; log a `consolidated` audit event with before/after counts (no content/PHI).

### 7.1 Expiration / cleanup policy (documented + justified)
- **TTL:** every entry key carries a **90-day TTL**, **refreshed on recall** (`touch`). Rationale: operational corrections go stale (a Monday-morning outage gets fixed); a sliding TTL keeps *actively useful* memories alive and lets dead ones expire automatically — Redis enforces it with zero cron. It also satisfies **GDPR data-minimization / storage-limitation**: nothing lingers indefinitely.
- **Usage decay:** the `recall_count==0 && age>30d` discard (step 3) prunes never-used entries earlier than TTL.
- **Hard cap:** `memory_max_entries_per_scope` (50) forces consolidation so a scope can't grow unbounded even if everything is recalled.
- **Why these values:** 90-day TTL ≈ a clinic quarter (protocols reviewed quarterly); 30-day zero-recall prune matches a monthly ops cycle; 50/scope keeps the injected top-k meaningful and the recall index small. All are `settings`-tunable.

---

## 8. Logging & audit (PHI-free)

- Every proposal (shown or PHI-rejected), every decision (approve/edit/reject/dismiss), and every consolidation event → an entry on the Redis **`mem_audit`** stream: `{ ts, event, staff_id, clinic_id, proposal_id, decision, reasons }`. **Never** store the raw memory text if it was PHI-rejected — store `redact_pii(text)` truncated + the rejection reason only.
- Reuse the harness `observability` structured logger for a parallel app-log line (`guardrail:"memory_proposal"`), so memory events show up alongside guardrail events; counts are additive, not in the guardrail metric buckets.
- **Never log** the bearer token or raw PHI; `redact_pii` all previews.

---

## 9. Scope identity & graph integration

### 9.1 Identity
- **staff_id** = the authenticated JWT `user_id` (already threaded into `service.invoke_graph`).
- **clinic_id** = the user record's `clinic_id`. The users store is **TinyDB** (`app/domains/users/store.py`) — **add a `clinic_id` field** to the user schema and seed data; `service` resolves it via `store.get_by_id(user_id)`. If a user has no clinic, fall back to `clinic_id="unassigned"` and log a warning (memory still works, scoped to staff).

### 9.2 New nodes & edges (extend the harness graph)
```
receive_question --> memory_consent_check          # NEW: resolve any pending proposal first
memory_consent_check --route--> {input_guards (normal/new_question), observability (consent resolved → confirm/END)}
input_guards --after_input_guards--> {memory_read, observability}   # memory_read replaces the direct hop to classify
memory_read --> classify                            # NEW: inject [MEMORY] block, read-only
… (classify → tools/retrieve → gather → external_content → compose) …
compose --> output_guards
output_guards --> memory_propose                    # NEW: self-eval + PHI validate + maybe ask consent
memory_propose --> observability --> END
```
- `memory_read` and `memory_propose` are **no-raise**; a Redis/Qdrant outage degrades to "no memory this turn", never blocks answering. Recompile at import; keep `MemorySaver` (pending state lives in Redis, so no durable graph checkpointer is required).
- Guardrails still run first: a jailbreak/PHI/personal input is blocked **before** `memory_read`/`memory_propose`.

---

## 10. Endpoints & response contract

- **`POST /api/v1/agent/query`** — unchanged request. Response gains an optional **`memory_proposal`**:
  ```json
  { "answer": "…", "trace_id": "run-…", "sources": [...], "sources_used": [...],
    "memory_proposal": { "id": "mp-…", "text": "Referral submissions fail Monday mornings…", "options": ["approve","edit","reject"] } }
  ```
  `memory_proposal` is present only when a proposal survived PHI validation and awaits consent; otherwise `null`.
- **`POST /api/v1/agent/memory/decision`** (optional, buttons path) — `{ proposal_id, decision: "approve"|"edit"|"reject", edited_text? } → { status }`.
- **`GET /api/v1/agent/memory`** — list the caller's scoped memories (read-only, for a "what do you remember?" view).
- All under the agent router's existing auth. No PHI ever leaves these endpoints.

---

## 11. Two documented flow cycles (Requirement 5)

Put these in `services/api/app/domains/agent/memory/README.md`.

### Cycle A — memory update **approved**
1. Staff (clinic `north`, user `42`): *"Heads up — referrals keep failing Monday mornings, tell people to retry after 11."*
2. Guardrails pass (no PHI/jailbreak). `memory_read`: nothing relevant yet. Agent answers normally.
3. `memory_propose` → `{worth_remembering:true, type:"semantic", memory_text:"Referral submissions fail Monday mornings; retry after 11am."}`. `validate_no_phi` → ok. Pending saved (`mem_pending:42`, TTL 30m). Answer appends the consent question; `memory_proposal` returned. Audit: `proposed`.
4. Next turn, staff: *"approve"*. `memory_consent_check` → consent classifier → `approve`. `validate_no_phi` again → ok → `store.write(scope=north/42, …)` + embed into `agent_memory`. Agent: *"Saved."* Audit: `approved`.
5. Later, staff: *"Any known issues with referrals?"* → `memory_read` recalls the entry, injects `[MEMORY]`, answer reflects it; `touch()` refreshes TTL.

### Cycle B — memory update **not approved**
- **B1 (explicit reject):** proposal shown as in A; next turn staff: *"no, don't save that."* → classifier `reject` → discarded, nothing written. Audit: `rejected`.
- **B2 (ignored → disregard):** proposal shown; next turn staff types a **new question** *"What's our AXA coverage in the UK?"* → classifier `new_question` → proposal **disregarded**, the new question answered normally. Audit: `dismissed_ignored`. (If the staff never returns, `mem_pending:42` expires in 30m.)
- **B3 (PHI auto-reject):** staff: *"Patient Johnson cancelled tomorrow, note that down."* → `memory_propose` proposes it → `validate_no_phi` **fails** → **never shown**, agent replies it can't store patient information, memory untouched. Audit: `phi_rejected` (redacted preview only).

---

## 12. Constraints & guardrails

- **Explicit read/write interface;** memory is injected as a bounded `[MEMORY]` block in the *user* message, **never** appended to the system prompt. Recall is scoped + top-k.
- **PHI/HIPAA/UK GDPR is absolute:** no patient identifier or PHI in any memory entry, audit record, endpoint, log, or output. PHI validation runs **before showing** a proposal **and before writing** any consolidation. PHI proposals are hard-rejected + logged, never dismissed silently.
- **Consent required** to write; approve/edit/reject; ignoring disregards; **every proposal + decision logged.**
- **Reuse existing classifiers** (route/scope) for the memory proposal and consent-intent steps; reuse `redact_pii` + harness `detect_phi` for PHI validation. No new HITL/memory framework.
- **Scope isolation:** a staff/clinic only ever reads its own memories; recall filters by `clinic_id`+`staff_id`.
- **No-raise nodes;** Redis/Qdrant outage → "no memory this turn", answering never blocked. Guardrails run before memory nodes.
- **Bounded memory:** consolidation + TTL + hard cap; documented expiration policy.
- **Redis is source of truth;** Qdrant recall index is rebuildable. Deleting/expiring an entry removes its vector.
- **Style:** `from __future__ import annotations`, typed, module `logger`, Pydantic — match the repo.

---

## 13. Dependencies & environment

- **New package:** `redis>=5` (+ its async client if the graph nodes are async). Qdrant client already present.
- **New dev/test package:** `fakeredis` (offline store tests, §15.1) — pin a version with `GETDEL` + stream support.
- **New infra:** a `redis` service in `docker-compose.yml` (dev: `redis:7-alpine`, no auth locally; document a password/TLS for non-dev).
- **New settings** (`app/core/config.py`, documented in `.example.env`):
  ```
  memory_enabled: bool = True                     # kill-switch (nodes pass through)
  redis_url: str = "redis://localhost:6379/0"
  memory_qdrant_collection: str = "agent_memory"
  memory_recall_k: int = 5
  memory_entry_ttl_days: int = 90
  memory_pending_ttl_minutes: int = 30
  memory_max_entries_per_scope: int = 50
  memory_dedupe_threshold: float = 0.92
  memory_low_relevance_days: int = 30
  memory_summarize_min_cluster: int = 3
  ```
- Reuse `settings.embedding_model` / `settings.generation_model` (no new model config). Missing Redis → memory disabled gracefully (log once), agent still answers.

---

## 14. Development workflow

```bash
git fetch origin
git checkout -b feature/agent_memory origin/feature/agent_harness

# 1) docker-compose: add redis; uv add redis; add clinic_id to user schema/seed
# 2) memory/schemas.py + store.py (RedisQdrantMemoryStore: read/write/list/delete/touch/pending)
# 3) memory/phi.py (wrap harness detect_phi + redact_pii) ; memory/audit.py (Redis stream)
# 4) memory/proposal.py (classifier-style self-eval) ; memory/consent.py (consent-intent classifier)
# 5) graph: memory_consent_check, memory_read, memory_propose nodes + edges; recompile
# 6) schemas/router/service: memory_proposal in response; /agent/memory[/decision] endpoints
# 7) memory/consolidate.py + a `uv run` consolidation script (+ suggested nightly schedule)

# bring up redis + run
docker compose up -d redis
uv run pytest services/api/tests/test_agent_memory.py tests/pipelines/test_memory_consent.py -q
uv run pytest tests/pipelines/test_guardrails_injection.py tests/pipelines/test_rag.py -q   # stay green
uv run uvicorn app.main:app --reload
#  Cycle A: "referrals fail monday mornings…" -> proposal -> "approve" -> recall next turn
#  Cycle B: proposal -> new question (disregard) ; PHI proposal -> auto-reject
```
Commit granularly: (a) infra+store, (b) PHI+audit, (c) proposal+consent, (d) graph wiring, (e) endpoints, (f) consolidation, (g) tests+README cycles.

---

## 15. Testing

- **`services/api/tests/test_agent_memory.py`** — store read/write/scoping/TTL (fakeredis or a test Redis); Qdrant recall stubbed; delete removes the vector; `list` scoped.
- **`tests/pipelines/test_memory_consent.py`** (build-relevant) — stub the LLM proposal/consent classifiers:
  - proposal worth remembering → consent question + pending saved;
  - approve → entry written + audit `approved`;
  - reject → nothing written + audit `rejected`;
  - **new_question → proposal disregarded, new question answered** (audit `dismissed_ignored`);
  - **PHI proposal → never shown, audit `phi_rejected`, memory empty**;
  - the **3 dismissible examples (§5.2) → `worth_remembering:false`, no prompt**.
- **Consolidation** — seed >cap entries incl. near-duplicates → dedupe/summarize/expire; a PHI-laced consolidation is discarded.
- Guardrail + RAG suites stay green; memory nodes stubbed to pass-through where a routing assertion is about non-memory behavior.

### 15.1 `fakeredis` test fixture (no live Redis)

Use **`fakeredis`** (dev/test dep) so the store tests run offline and in CI. It implements Hash/Sorted-Set/String/Stream, `EXPIRE`/TTL, and `GETDEL`, so Appendix A works unchanged. Inject the client into `RedisQdrantMemoryStore` (constructor takes a `redis_client` and a `qdrant_client`; production wires the real ones from settings, tests pass fakes) and **stub Qdrant** with a tiny in-memory double so recall is deterministic.

```python
# services/api/tests/conftest.py  (or test_agent_memory.py)
import time
import pytest
import fakeredis                                   # uv add --dev fakeredis
from app.domains.agent.memory.store import RedisQdrantMemoryStore
from app.domains.agent.memory.schemas import MemoryEntry, MemoryScope


class FakeQdrant:
    """Minimal Qdrant double: stores {mem_id: (scope, type)}, recall returns by insertion order."""
    def __init__(self): self.points: dict[str, dict] = {}
    def upsert(self, collection, points):
        for p in points: self.points[p.id] = p.payload
    def delete(self, collection, points_selector):
        for mid in points_selector: self.points.pop(mid, None)
    def search(self, collection, query_vector, query_filter=None, limit=5):
        c = _flt(query_filter, "clinic_id"); s = _flt(query_filter, "staff_id")
        hits = [type("H", (), {"payload": pl})
                for pl in self.points.values()
                if pl["clinic_id"] == c and pl["staff_id"] == s]
        return hits[:limit]


@pytest.fixture
def store():
    r = fakeredis.FakeStrictRedis(decode_responses=True)     # server_type='redis' → GETDEL/streams OK
    s = RedisQdrantMemoryStore(redis_client=r, qdrant_client=FakeQdrant(),
                               embed_fn=lambda text: [0.0])   # embeddings irrelevant to the fake search
    yield s
    r.flushall()


def _now(): return int(time.time())


def test_write_read_scoped(store):
    scope = MemoryScope(clinic_id="north", staff_id="42")
    entry = MemoryEntry(id="m-1", scope=scope, type="semantic",
                        text="Referrals fail Monday mornings; retry after 11am.",
                        created_at=_now(), last_recalled_at=_now(), recall_count=0)
    store.write(scope, entry)
    # other-scope caller sees nothing
    assert store.read(MemoryScope(clinic_id="south", staff_id="99"), "referrals") == []
    got = store.read(scope, "referral problems")
    assert got and got[0].id == "m-1"


def test_ttl_and_touch_refresh(store):
    scope = MemoryScope(clinic_id="north", staff_id="42")
    store.write(scope, MemoryEntry(id="m-1", scope=scope, type="semantic", text="x",
                                   created_at=_now(), last_recalled_at=_now(), recall_count=0))
    key = "mem:entry:north:42:m-1"
    assert store._redis.ttl(key) > 0                          # per-key TTL set (A.2)
    store.touch(scope, "m-1")
    assert int(store._redis.hget(key, "recall_count")) == 1   # A.3 sliding refresh


def test_pending_getdel_pop(store):
    store.save_pending("42", _proposal())                     # SET … EX (A.5)
    assert store.pop_pending("42") is not None                # GETDEL
    assert store.pop_pending("42") is None                    # gone after pop → "disregard" path


def test_expiry_reconciles_index(store):
    scope = MemoryScope(clinic_id="north", staff_id="42")
    store.write(scope, MemoryEntry(id="m-1", scope=scope, type="semantic", text="x",
                                   created_at=_now(), last_recalled_at=_now(), recall_count=0))
    store._redis.delete("mem:entry:north:42:m-1")             # simulate TTL expiry
    assert store.list(scope) == []                            # list() ZREMs the straggler (A.4)
```

> Notes: use a `fakeredis` version new enough for **`GETDEL`** and **streams** (`XADD`/`XRANGE`); pin it in the dev group. Assert audit via `store._redis.xrange("mem:audit")` for the `proposed`/`approved`/`phi_rejected` events. The `test_memory_consent.py` graph tests reuse this `store` fixture and additionally stub `proposal.propose_fn` / `consent.classify_fn` (the classifier seams) for deterministic decisions.

---

## 16. Suggested additional tasks (improve outcomes)

1. **Memory recall in the trace** — add `memory_read`/`memory_propose` to `trace_steps` and surface recalled `mem_id`s in LangSmith for auditability.
2. **Relevance-weighted recall** — rank by similarity × recency × `recall_count` so durable, frequently-used corrections win the top-k.
3. **Contradiction detection** — when a new proposal contradicts an existing entry (e.g., "referrals now fixed"), offer to *replace* rather than add; keeps memory truthful.
4. **Per-clinic vs per-staff split at read** — merge staff-scoped procedural prefs with clinic-scoped semantic facts, clearly labeled, so one staff's preference never leaks as clinic policy.
5. **Consent fatigue guard** — rate-limit proposals per session; only propose high-confidence items (`worth_remembering` + a confidence threshold) to avoid nagging.
6. **Second PHI detector** — optional Presidio pass behind `memory_enabled` for higher-recall PHI screening on proposals/consolidations.
7. **Right-to-be-forgotten endpoint** — `DELETE /api/v1/agent/memory/{id}` and a per-scope purge, for GDPR erasure requests; audit the deletion.
8. **Frontend memory panel** — a "What I remember for this clinic" view (list + delete) in the Knowledge Assistant, plus inline Approve/Edit/Reject on the proposal.
9. **Replay/consolidation eval** — an offline harness that checks consolidated summaries preserve the operational facts and introduce no PHI (LLM-judge + PHI scan).

---

## 17. Model recommendations for this use case

New LLM jobs: memory proposal, consent-intent classification, consolidation summarization (PHI validation stays deterministic — reuse the harness).

- **Memory proposal + consent-intent classifier** — fast, cheap, reliable **structured JSON + short classification**. **Claude Haiku 4.5** is the strong default (instruction/JSON adherence, low latency); the current `deepseek-v4-flash` is acceptable if it returns clean JSON. Temperature 0.
- **Consolidation summarizer** — faithfulness matters (must preserve operational facts, invent nothing, leak no PHI). **Claude Sonnet 4.x** for the summarization/dedup pass; Haiku 4.5 if cost-bound.
- **Embeddings** — reuse **`pplx-embed-v1`** for `agent_memory` (same space as RAG); do not introduce a second embedding model.
- **PHI validation** — **not an LLM** by default (deterministic harness); an LLM/Presidio pass is an optional second opinion (§16.6).
- All are `settings.*_model` string changes through the existing proxy — verify ids before switching.

---

## 18. Assumptions & open items

- **Backend = Redis (system-of-record + audit + pending consent, native TTL) + Qdrant (semantic recall).** Redis is **new infra** (add the service + client). — *confirmed direction (Redis/KV/VectorDB combination).*
- **"Intent clarification" = reuse the existing scope + route classifiers**: the memory proposal and the consent-reply interpretation are new classifier-style LLM nodes following that pattern. There is **no pre-existing HITL/clarification component** in the agent to import — this builds the consent step on the classifier pattern. — *confirmed direction.*
- **Turn model (recommended):** pending proposal persisted in **Redis keyed by `staff_id` with a 30-min TTL**; a `memory_consent_check` node resolves it on the next turn via the consent classifier. No durable LangGraph checkpointer needed (pending state is in Redis, not the graph checkpoint). — *recommended; confirm if you prefer a `proposal_id` round-trip instead.*
- **Scope:** `staff_id` = JWT `user_id`; `clinic_id` = user record field. The users store is **TinyDB** and has **no `clinic_id` today** — this adds it to the schema/seed; users without a clinic fall back to `unassigned`. — *confirm the clinic source; adjust seed.*
- **PHI validation** reuses the harness `detect_phi` heuristics (English-name/quasi-identifier shaped) — tune recall against the graded memory PHI cases; Presidio is the upgrade path. — *tune during implementation.*
- **Base branch `feature/agent_harness`** (latest with guardrails + MCP). — *confirm.*
- **Consolidation trigger:** on hard-cap breach + a suggested nightly job; if the repo's job runner (`domains/jobs`) is available, wire it there. — *confirm scheduling mechanism.*

---

## 19. Acceptance / validation checklist

- [ ] Work on `feature/agent_memory`, branched off `feature/agent_harness`.
- [ ] Memory architecture selected + justified (Redis system-of-record + audit + pending consent with TTL; Qdrant `agent_memory` recall); choices documented (§2).
- [ ] Explicit `MemoryStore` interface (`read/write/list/delete/touch/pending`); recall is scoped + top-k and injected as a bounded `[MEMORY]` block — **not** appended to the system prompt.
- [ ] After each interaction, `memory_propose` self-evaluates (classifier-style JSON) with criteria; **3 dismissible examples** handled (one-off lookup, closing/chit-chat, PHI attempt) → no prompt.
- [ ] Consent flow reuses the scope/route classifier: approve / edit / reject; a new question disregards; pending expires (30m); **every proposal + decision logged** to `mem_audit` (PHI-free).
- [ ] PHI validation runs **before showing** a proposal **and before writing** any consolidation; PHI proposals hard-rejected + logged, never shown.
- [ ] Consolidation (dedupe + summarize + discard-low-relevance) keeps memory bounded; **expiration/cleanup policy documented + justified** (90-day sliding TTL, 30-day zero-recall prune, 50/scope cap).
- [ ] **Two flow cycles documented** — one approved, one not (reject / ignore-disregard / PHI auto-reject) — in the memory README.
- [ ] Scope = `user_id` (staff) + `clinic_id` (user record; field added to the TinyDB schema/seed).
- [ ] `memory_read`/`memory_propose`/`memory_consent_check` nodes wired; graph recompiles; `MemorySaver` retained; guardrails run before memory nodes; RAG + guardrail suites stay green.
- [ ] New `redis` dependency + docker-compose service + `.example.env` settings; Redis/Qdrant outage degrades gracefully; no PHI/token in logs.
```

---

## Appendix A — Redis key schema & commands (concrete data model)

All keys are namespaced under `mem:`. `clinic_id`/`staff_id` are lowercased opaque strings; `mem_id` = `"m-" + uuid4().hex[:12]`; `proposal_id` = `"mp-" + uuid4().hex[:12]`. Times are epoch-seconds (integers). **No PHI in any key, field, or stream — text fields hold only PHI-validated content; audit previews are `redact_pii`'d and truncated.**

### A.1 Keys at a glance
| Purpose | Key | Type | TTL |
|---|---|---|---|
| Memory entry | `mem:entry:{clinic_id}:{staff_id}:{mem_id}` | Hash | `memory_entry_ttl_days` (90d), refreshed on recall |
| Per-scope index | `mem:index:{clinic_id}:{staff_id}` | Sorted Set (score = `last_recalled_at`, member = `mem_id`) | none (pruned with entries) |
| Pending consent | `mem:pending:{staff_id}` | String (JSON) | `memory_pending_ttl_minutes` (30m) |
| Audit log | `mem:audit` | Stream | none (capped, `MAXLEN ~ 100000`) |
| Consolidation lock | `mem:lock:consolidate:{clinic_id}:{staff_id}` | String | 60s (SET NX EX) |

### A.2 Memory entry (Hash)
Fields: `id, clinic_id, staff_id, type, text, created_at, last_recalled_at, recall_count, source_trace_id`.
```
# WRITE (after consent + PHI ok) — atomic via pipeline/MULTI
HSET   mem:entry:north:42:m-ab12cd34ef56 \
       id m-ab12cd34ef56 clinic_id north staff_id 42 type semantic \
       text "Referral submissions fail Monday mornings; retry after 11am." \
       created_at 1785600000 last_recalled_at 1785600000 recall_count 0 \
       source_trace_id run-9f3c1a2b7d40
EXPIRE mem:entry:north:42:m-ab12cd34ef56 7776000          # 90d
ZADD   mem:index:north:42 1785600000 m-ab12cd34ef56
```
```python
# redis-py (sync) equivalent — one round-trip
key = f"mem:entry:{c}:{s}:{mid}"
pipe = r.pipeline()
pipe.hset(key, mapping=entry.model_dump(mode="json"))
pipe.expire(key, settings.memory_entry_ttl_days * 86400)
pipe.zadd(f"mem:index:{c}:{s}", {mid: entry.last_recalled_at})
pipe.execute()
```

### A.3 Recall + `touch` (refresh TTL, bump stats)
Semantic recall is a Qdrant search (A.6) that returns `mem_id`s; hydrate + touch from Redis:
```python
# hydrate top-k
entries = [r.hgetall(f"mem:entry:{c}:{s}:{mid}") for mid in recalled_ids if r.exists(...)]
# touch each recalled entry (sliding TTL + recency + count)
now = int(time.time())
pipe = r.pipeline()
for mid in recalled_ids:
    k = f"mem:entry:{c}:{s}:{mid}"
    pipe.hincrby(k, "recall_count", 1)
    pipe.hset(k, "last_recalled_at", now)
    pipe.expire(k, settings.memory_entry_ttl_days * 86400)   # refresh sliding TTL
    pipe.zadd(f"mem:index:{c}:{s}", {mid: now})
pipe.execute()
```

### A.4 List / delete / expire
```
# LIST a scope (most-recent first)
ZREVRANGE mem:index:north:42 0 -1
#   → then HGETALL each mem:entry:north:42:{mid}  (skip ids whose key has expired: ZREM the stragglers)

# DELETE one (also drop the Qdrant point — A.6)
DEL   mem:entry:north:42:m-ab12cd34ef56
ZREM  mem:index:north:42 m-ab12cd34ef56

# EXPIRY is automatic (per-key TTL). A weep/cleanup pass reconciles the index:
#   for mid in ZRANGE index: if not EXISTS entry-key → ZREM index mid  (and delete its Qdrant point)
```

### A.5 Pending consent (String + TTL)
```
# SAVE when a proposal survives PHI validation and awaits consent
SET mem:pending:42 '{"proposal_id":"mp-77aa","clinic_id":"north","staff_id":"42",
     "type":"semantic","text":"Referral submissions fail Monday mornings; retry after 11am.",
     "source_trace_id":"run-9f3c1a2b7d40","created_at":1785600000}' EX 1800

# NEXT TURN — pop-and-resolve (GETDEL is atomic; the consent classifier reads the popped value)
GETDEL mem:pending:42        # returns JSON or nil; nil ⇒ no pending (expired/none) ⇒ normal routing
```
> `GETDEL` (Redis ≥6.2) makes "pop the pending proposal" atomic. `new_question`/`reject` simply discard the popped value (+ audit); `approve`/`edit` proceed to A.2 write. If Redis <6.2, use `GET` + `DEL` in a `MULTI`.

### A.6 Qdrant recall index (`agent_memory` collection)
```python
# WRITE (after A.2): point id = mem_id, vector = embed(text), payload = scope+type (NO text/PHI needed for filtering)
qdrant.upsert("agent_memory", points=[PointStruct(
    id=mid, vector=embed(entry.text),
    payload={"mem_id": mid, "clinic_id": c, "staff_id": s, "type": entry.type})])

# READ (scoped top-k)
hits = qdrant.search("agent_memory", query_vector=embed(question),
    query_filter=Filter(must=[FieldCondition(key="clinic_id", match=MatchValue(value=c)),
                              FieldCondition(key="staff_id",  match=MatchValue(value=s))]),
    limit=settings.memory_recall_k)
recalled_ids = [h.payload["mem_id"] for h in hits]

# DELETE / EXPIRE reconciliation: qdrant.delete("agent_memory", points_selector=[mid])
```
> Payload holds only `mem_id`+scope+type — the recall vector is derived from text, but the **text itself lives only in Redis**, so a Qdrant leak exposes no memory content.

### A.7 Audit stream (append-only, PHI-free)
```
XADD mem:audit MAXLEN '~' 100000 * \
     event proposed   proposal_id mp-77aa clinic_id north staff_id 42 \
     ts 1785600000 preview "Referral submissions fail Monday mornings; retry a…"
XADD mem:audit MAXLEN '~' 100000 * event approved proposal_id mp-77aa mem_id m-ab12cd34ef56 staff_id 42 ts 1785600200
XADD mem:audit MAXLEN '~' 100000 * event phi_rejected proposal_id mp-90bc staff_id 42 ts 1785600300 reasons "phi:name+age+clinic"
XADD mem:audit MAXLEN '~' 100000 * event dismissed_ignored proposal_id mp-77aa staff_id 42 ts 1785600400
XADD mem:audit MAXLEN '~' 100000 * event consolidated clinic_id north staff_id 42 before 52 after 41 ts 1785700000
```
- `event ∈ {proposed, approved, edited, rejected, dismissed_ignored, phi_rejected, phi_rejected_consolidation, consolidated, deleted}`.
- `preview` is `redact_pii(text)[:80]`; **omit `preview` entirely on `phi_rejected`** (store only `reasons`, never the offending text).
- Read the log with `XRANGE mem:audit - +` or tail with `XREVRANGE mem:audit + - COUNT n`.

### A.8 Consolidation lock (avoid concurrent rewrites)
```
SET mem:lock:consolidate:north:42 <run_id> NX EX 60     # acquire; skip if already held
# … dedupe/summarize/expire (§7), re-validate PHI, rewrite entries (A.2) + Qdrant (A.6) …
DEL mem:lock:consolidate:north:42                        # release (or let the 60s TTL expire)
```

> **Atomicity note:** entry write (A.2) and its Qdrant upsert (A.6) are two stores — write Redis first (source of truth), then Qdrant; if the Qdrant upsert fails, log and let the reconciliation pass (A.4) re-index from Redis. Never leave a Qdrant point without its Redis entry.
