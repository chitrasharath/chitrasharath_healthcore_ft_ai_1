# Spec — HealthCore Support Agent on LangGraph (`feature/agent_rag_langgraph`)

> **Audience:** a coding agent implementing this feature end-to-end.
> **Reference guide:** `4GeeksAcademy/ai-engineering-syllabus` → `content/projects/ai-eng-langgraph-agent-base/.learn/solution/README.md`.
> **Non-negotiable framing:** reproduce the *exact behavior* of the existing RAG, but expressed as a compiled LangGraph graph. Reuse the existing retrieval/generation code; do not reimplement RAG logic.

---

## 1. Project overview

HealthCore is a FastAPI backend (`services/api`) with a working RAG "knowledge assistant" that answers front-desk/coordinator questions from a curated company knowledge base (appointment policy, insurance coverage, referral process, new-patient checklist). Retrieval is dense vectors in a local Qdrant collection; generation is an OpenAI-compatible chat completion through the 4Geeks LLM proxy. The RAG is exposed today at `POST /api/v1/knowledge/query` behind auth.

This feature re-expresses that same request→retrieve→generate flow as an explicit **LangGraph** state graph with named nodes, real conditional routing, a compiled+checkpointed graph, LangSmith tracing, trace-based evals, and a new endpoint `POST /agent/query` that coexists with the RAG endpoint. **Nothing about the existing RAG endpoint or its tests may change in observable behavior.**

### Why a graph (what "same behavior" means)
The graph must produce, for the same question:
- the **same grounded answer** the RAG produces (because it calls the *same* retrieval and the *same* generation code), and
- the **same fallback behavior** when nothing relevant is retrieved (the agent uses its own required fallback string — see §6.3).

---

## 2. Tech stack

| Layer | Choice (existing) | Notes |
|---|---|---|
| Language / runtime | Python `>=3.12` | `services/api/pyproject.toml` |
| Package manager | `uv` | lockfile `services/api/uv.lock` |
| Web framework | FastAPI + Uvicorn | `services/api/app` |
| Config | `pydantic-settings` `Settings` | `services/api/app/core/config.py`, `.env` |
| Vector DB | Qdrant (local path mode) | `data/process/rag.py` |
| Embeddings | `pplx-embed-v1` via proxy | `settings.embedding_model` |
| Generation | `deepseek-v4-flash` via proxy | `settings.generation_model`, OpenAI-compatible `/v1/chat/completions` at `settings.llm_base_url` (`https://llm.4geeks.ai`) |
| **New: orchestration** | **LangGraph** (`langgraph`, `langchain-core`) | to be added |
| **New: tracing** | **LangSmith** (`langsmith` + `LANGCHAIN_*` env) | in-state trace is source of truth for evals; LangSmith is the added observability layer |
| Tests | `pytest` | `services/api/tests/`, `tests/pipelines/` |

---

## 3. Existing code the agent MUST reuse (do not reimplement)

All in the repo at these paths (verified on `origin/feature/rag`):

**`data/pipelines/rag.py`**
- `normalize_query(question) -> str` — trims/collapses whitespace, raises `ValueError` on empty, enforces max length.
- `retrieve(query, *, top_k=None, min_score=None, ...) -> list[dict]` — embeds (with `expand_query_for_retrieval`), queries Qdrant, **filters out any hit below `settings.rag_min_score` (default `0.30`)**, returns payload dicts with a `"score"` key, sorted desc. **An empty list already means "no context above threshold."**
- `query(question, ...) -> QueryResult` — the monolithic pipeline. **The agent nodes must NOT call this.** It will be refactored (see §5).
- `_generate(assembled_prompt) -> str` — POSTs to the proxy; raises `GenerationError` / `RagConfigError`.
- `_build_context_block(hits) -> str`, `_dedupe_sources(hits) -> list[dict]`.
- Constants: `FALLBACK_ANSWER`, `SYSTEM_PROMPT`. Exceptions: `GenerationError`, `RagConfigError`.
- `QueryResult` dataclass: `answer, sources, context_texts, assembled_prompt, model, temperature`.

**`data/process/rag.py`** — `embed`, `get_qdrant_client`, `bootstrap_env`, `setup`, `collection_is_populated`, `EmbeddingError`, `RagConfigError`, `_REPO_ROOT`.

**`services/api/app/core/config.py`** — `settings` with: `llm_base_url`, `llm_api_key`, `generation_model`, `embedding_model`, `qdrant_path`, `qdrant_collection`, `rag_top_k=3`, `rag_min_score=0.30`, `rag_generation_temperature=0.15`, `rag_question_max_length=1000`.

**`services/api/app/core/dependencies.py`** — `get_current_user` (auth dependency used by the knowledge router).

**Eval scaffolding** — `data/eval/run_eval.py`, `data/eval/test-queries.json` (fields per item: `question`, `should_abstain`, `expected_source_document`), `tests/pipelines/test_rag.py`.

---

## 4. Scope

### In scope
- Refactor `query()` to expose a reusable `generate_answer(question, context)` (behavior-preserving).
- New `app/domains/agent/` package: state, nodes, edges, compiled+checkpointed graph, tracing.
- Wire LangSmith tracing via env.
- New endpoint `POST /api/v1/agent/query`, mounted on `api_v1_router` at the same level as the knowledge router.
- 3 evals asserting against the trace; ≥1 asserts answer grounding.
- Add `langgraph` (+ `langsmith`) to deps.

### Out of scope
- No change to RAG retrieval math, prompts, thresholds, or the knowledge endpoint contract.
- No new vector store, no re-embedding, no schema migration.
- No multi-turn memory beyond what checkpointing provides (state schema is per-question; see §6.1).
- No frontend work.

---

## 5. Refactor: factor `generate_answer` out of `query()` (behavior-preserving)

**Decision:** refactor `query()` to delegate to a new `generate_answer` so there is a single generation path. **`tests/pipelines/test_rag.py` must pass unchanged** — that is the guardrail proving behavior preservation.

In `data/pipelines/rag.py`, extract the prompt-assembly + generation step:

```python
def build_assembled_prompt(question: str, hits: list[dict[str, Any]]) -> str:
    """Assemble the SOURCE-CONTEXT + QUESTION prompt (moved verbatim from query())."""
    context = _build_context_block(hits)
    return (
        f"SOURCE CONTEXT (every fact you state must come from a labeled block):\n\n"
        f"{context}\n\n"
        f"QUESTION:\n{question}\n"
    )

def generate_answer(
    question: str,
    context: list[dict[str, Any]],
    *,
    generate_fn=_generate,
) -> str:
    """Generate a grounded answer from already-retrieved context.

    `context` is the list of hit dicts returned by `retrieve()`. Callers that
    have no context must NOT call this — routing handles the no-context case.
    """
    assembled = build_assembled_prompt(question, context)
    return generate_fn(assembled)
```

Then `query()` calls `generate_answer` instead of inlining `_generate` (it may still call `build_assembled_prompt` once to populate `QueryResult.assembled_prompt`). Keep the injectable `generate_fn` seam — the routing evals depend on it (§8).

Export `generate_answer` and `build_assembled_prompt` in `__all__`.

> **Requirement restated:** the agent's generation node calls `generate_answer(question, context)`. It must **never** call `query()`.

---

## 6. LangGraph design

New package: **`services/api/app/domains/agent/`**

```
app/domains/agent/
  __init__.py
  state.py       # AgentState TypedDict
  nodes.py       # receive_question, retrieve_node, query_node, no_context_node
  routing.py     # after_receive, after_retrieve (conditional edge functions)
  graph.py       # build + compile (MemorySaver), module-level compiled singleton
  tracing.py     # trace_step helper + LangSmith env wiring
  schemas.py     # AgentQueryRequest / AgentQueryResponse
  service.py     # invoke_graph(question) -> response; error handling
  router.py      # POST /agent/query
```

### 6.1 State (`state.py`)

Minimal state — only what nodes need. `trace_steps` accumulates via a reducer (the **in-state trace** the evals assert against).

```python
import operator
from typing import Annotated, Any, Sequence, TypedDict

class AgentState(TypedDict):
    question: str                                   # raw question as received
    normalized_question: str | None                 # after receive_question
    retrieved_context: list[dict[str, Any]] | None  # hits from retrieve()
    answer: str | None
    sources: list[dict[str, Any]] | None            # deduped, for endpoint parity
    trace_id: str                                   # uuid per invocation
    trace_steps: Annotated[Sequence[dict[str, Any]], operator.add]
    error: str | None
```

### 6.2 Nodes (`nodes.py`)

Each node is single-responsibility and appends exactly one trace step (via `tracing.trace_step`). **Never one node doing retrieve + generate silently.**

1. **`receive_question(state)`** — normalize/validate the raw question using `normalize_query`. On success set `normalized_question` and append a `receive_question` trace step. On empty/invalid (`ValueError`), set `error="empty_question"` (do **not** raise) and append the step; routing sends to END.
2. **`retrieve_node(state)`** — call `data.pipelines.rag.retrieve(normalized_question)` (reuse; do not pass a lowered threshold). Set `retrieved_context` (may be `[]`), append a `retrieve` trace step whose summary includes the hit count. On `EmbeddingError`/`RagConfigError`, set `error` and append the step.
3. **`query_node`** — call `generate_answer(normalized_question, retrieved_context)`; set `answer` and `sources = _dedupe_sources(retrieved_context)`; append a `query` trace step. On `GenerationError`/`RagConfigError`, set `error` and append the step.
4. **`no_context_node`** — set `answer = AGENT_NO_CONTEXT_ANSWER` (see §6.3), `sources = []`; append a `no_context` trace step. **Does not call the LLM.**

Trace step shape (from the reference guide):
```python
{"node": "retrieve", "order": 2, "output_summary": "3 hits >= 0.30"}
```

### 6.3 The required fallback string

```python
AGENT_NO_CONTEXT_ANSWER = "I don't have information about that."
```
Use this **exact** string in `no_context_node` (the task specifies it). It is intentionally distinct from RAG's `FALLBACK_ANSWER`; do not swap one for the other.

### 6.4 Routing / conditional edges (`routing.py`) — **at least one REAL condition**

Two conditional-edge functions with genuine data-driven conditions:

```python
def after_receive(state) -> str:
    # REAL condition #1: empty/invalid question short-circuits to END
    if state.get("error") == "empty_question" or not state.get("normalized_question"):
        return "end"
    return "retrieve"

def after_retrieve(state) -> str:
    if state.get("error"):
        return "end"                      # upstream retrieval failure
    # REAL condition #2: no context above threshold -> the "I don't have information..." node
    if not state.get("retrieved_context"):
        return "no_context"
    return "query"
```

> `retrieve()` already drops hits `< rag_min_score`, so `retrieved_context == []` is precisely "no context above threshold." Do not re-threshold in the node.

### 6.5 Graph assembly + compile + checkpoint (`graph.py`)

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("receive_question", receive_question)
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("query", query_node)
    builder.add_node("no_context", no_context_node)

    builder.set_entry_point("receive_question")
    builder.add_conditional_edges("receive_question", after_receive,
                                  {"retrieve": "retrieve", "end": END})
    builder.add_conditional_edges("retrieve", after_retrieve,
                                  {"query": "query", "no_context": "no_context", "end": END})
    builder.add_edge("query", END)
    builder.add_edge("no_context", END)

    checkpointer = MemorySaver()                 # checkpointing requirement
    return builder.compile(checkpointer=checkpointer)   # compile BEFORE execution

# Compile once at import (module load). Structural errors raise HERE, at startup,
# not per request. Do NOT compile per request.
compiled_graph = build_graph()
```

**Compile-fails-on-structural-errors requirement:** `builder.compile()` raises on dangling nodes, unreachable nodes, or edges to unknown nodes. Because we compile at module import, such errors surface at app startup / test-collection time. Add a smoke test that imports `compiled_graph` and asserts it is not `None` (§8, eval 0 / sanity).

**Checkpointing:** every invocation passes a `thread_id` so the checkpointer persists state:
```python
config = {"configurable": {"thread_id": trace_id}}
final_state = compiled_graph.invoke(initial_state, config=config)
```

### 6.6 Tracing (`tracing.py`) — in-state + LangSmith

- **In-state trace (source of truth for evals):** `trace_step(node, order, summary) -> dict` returns the step dict; nodes return `{"trace_steps": [trace_step(...)], ...}` so the `operator.add` reducer accumulates them in order.
- **LangSmith (added observability layer):** when `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY` are set, LangGraph auto-exports runs to LangSmith — no per-node code needed. `tracing.py` reads/echoes: `LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT` (default `healthcore-agent`), `LANGCHAIN_ENDPOINT`. If the key is unset, tracing is silently disabled and the graph still runs — LangSmith must never be a hard runtime dependency. Add these to `services/api/.example.env`.

---

## 7. Endpoint contract

**Mount point:** register the agent router on **`api_v1_router`** in `services/api/app/api/v1/router.py`, **at the same level as the knowledge router** — with the same auth dependency:
```python
from app.domains.agent.router import router as agent_router
api_v1_router.include_router(agent_router, dependencies=[Depends(get_current_user)])
```
The agent router itself uses `prefix="/agent"`, so the effective path is `POST /api/v1/agent/query`, a sibling of `POST /api/v1/knowledge/query`.

> The task string writes `POST /agent/query`; in this repo that is realized as `/api/v1/agent/query` because every domain sits under the `/api/v1` prefix. Placing it beside the knowledge router keeps the two support endpoints at the same level and coexisting.

**Auth:** inherited from the v1 `include_router(..., dependencies=[Depends(get_current_user)])` exactly like the knowledge router — no per-route `Depends` needed. (Remove that dependency to make it public.)

**Request** (`schemas.py`):
```json
{ "question": "Do you take Medicaid in the US?" }
```
> Unlike the knowledge schema, allow an **empty/blank** `question` (`min_length=0`) so the empty-question conditional is actually exercised by the graph and its eval. Validation of empties happens in `receive_question`, not in Pydantic.

**Success (200):**
```json
{
  "answer": "…",
  "trace_id": "run-abc123",
  "sources": [{"source_document": "…", "section": "…", "score": 0.71}]
}
```
- Empty question → 200 with a clear message (e.g. `answer: "Please enter a question."`) and a `trace_id`; the trace shows execution ended without a `query` step.
- No context above threshold → 200 with `answer = "I don't have information about that."`, `sources: []`.

**Failure (graph raised / node set a hard error):** respond with a **clear message and no raw stack trace**. `service.invoke_graph` wraps `compiled_graph.invoke(...)` in try/except:
- Known upstream failures (`RagConfigError` → 503; `EmbeddingError`/`GenerationError` → 502) map like the knowledge service does.
- Any other exception → 500 with `{"detail": "The support agent is temporarily unavailable. Please try again."}`. Log the full exception server-side only.

`service.invoke_graph(question) -> AgentQueryResponse` builds `initial_state` (fresh `trace_id = "run-" + uuid4().hex[:12]`), invokes with the `thread_id` config, then maps `final_state` → response. If `final_state["error"]` is set to a hard failure, translate to the matching HTTPException.

---

## 8. Evals (≥3, trace-based; ≥1 grounding) — `tests/pipelines/test_agent_evals.py`

**Principle (from the task): evals run against the *trace*, not against a live execution.** Each eval invokes the compiled graph once, captures the returned `final_state` (especially `trace_steps`), and asserts against that captured artifact. Routing/order evals stub generation for determinism via the `generate_fn` seam; the grounding eval uses the real proxy.

Helper: `run_agent(question, *, generate_fn=None) -> final_state` that invokes `compiled_graph` with a unique `thread_id` and (for stubbed cases) injects a fake `generate_fn` into `query_node` (e.g. via monkeypatch on `generate_answer` or a settable node dependency — provide a clean seam).

| # | Name | Input | Asserts against trace | Type |
|---|---|---|---|---|
| 1 | **Node order / routing** | a known FAQ (from `test-queries.json`, `should_abstain=false`), generation stubbed | `trace_steps` node order is `receive_question → retrieve → query`; `retrieve` step precedes `query`; no `no_context` step | routing |
| 2 | **Empty-question error path** | `""` (or whitespace) | `trace_steps` contains `receive_question`, ends **without** a `query` step; `error == "empty_question"`; a clear message returned | routing |
| 3 | **Grounded answer (acceptance gate)** | a policy question with a known `expected_source_document` (e.g. a Medicaid/insurance question) | real generation: `answer` is non-empty, is **not** the no-context/fallback string, and **mentions the expected grounded entity** (e.g. the insurer/`$50`/`£40`/policy term from the source); `sources` includes `expected_source_document` | **grounding — required** |

Rules:
- Eval 3 is an **acceptance gate, not optional.** Trace/routing correctness (evals 1–2) does **not** substitute for grounding.
- Eval 3 requires `LLM_API_KEY` + a populated collection; follow the existing harness convention — **skip/xfail when `LLM_API_KEY` is unset** (mirror `data/eval/run_eval.py`), and `setup()` the collection if empty. Consider recording a fixture response so CI can run it offline.
- These agent evals are **in addition to** the existing RAG tests. `tests/pipelines/test_rag.py` and `services/api/tests/test_knowledge.py` must still pass.
- Add a sanity check that `graph.compiled_graph` imports without raising (proves compile-time structural validation).

---

## 9. Dependencies to add

In `services/api/pyproject.toml` `dependencies`:
```
"langgraph>=0.2.0",
"langsmith>=0.1.0",
```
`langchain-core` comes transitively with `langgraph`. Run `uv sync` (or `uv lock`) to update `services/api/uv.lock`. Do not pin exotic versions; use the current stable line and let the lockfile record exact versions.

New `.example.env` keys (append; never commit real secrets):
```
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=
LANGCHAIN_PROJECT=healthcore-agent
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
```

---

## 10. Constraints & guardrails

- **Reuse, don't reimplement:** retrieval, embedding, prompt, threshold, and generation logic come from `data/pipelines/rag.py` + `data/process/rag.py`. No copies.
- **`query_node` must call `generate_answer`, never `query()`.**
- **Behavior parity:** existing RAG endpoint + tests unchanged and passing.
- **Compile before execution**, once, at module load; structural errors must fail loudly at startup.
- **Checkpointer attached** (`MemorySaver`) with a per-request `thread_id`.
- **LangSmith optional at runtime:** missing key disables tracing gracefully; it is never required for the graph or endpoint to work.
- **No secrets in code or logs.** Reuse the existing PII redaction (`app.domains.knowledge.pii.redact_pii`) if you log questions/answers.
- **Error responses carry no stack traces.**
- **Endpoint delegates to the graph only** — no business logic in the router.
- Python `>=3.12`, `uv`-managed, matches existing code style (`from __future__ import annotations`, type hints, module-level `logger`).

---

## 11. Development workflow

```bash
# 1. Branch off feature/rag (NOT main) — required by the task
git fetch origin
git checkout -b feature/agent_rag_langgraph origin/feature/rag

# 2. Add deps + sync
cd services/api
uv add langgraph langsmith        # or edit pyproject.toml then: uv sync

# 3. Implement §5 refactor first, then the app/domains/agent package (§6),
#    then the endpoint (§7), then evals (§8).

# 4. Run the guardrail (RAG behavior preserved) + new evals
uv run pytest tests/pipelines/test_rag.py services/api/tests/test_knowledge.py -q   # must stay green
uv run pytest tests/pipelines/test_agent_evals.py -q

# 5. Grounding eval + full RAG eval (needs LLM_API_KEY + populated collection)
LLM_API_KEY=… uv run python data/eval/run_eval.py
LLM_API_KEY=… uv run pytest tests/pipelines/test_agent_evals.py -q

# 6. Manual smoke test of the endpoint
uv run uvicorn app.main:app --reload    # then POST /api/v1/agent/query with a bearer token
```

Commit granularly: (a) refactor + RAG tests green, (b) graph package, (c) endpoint, (d) evals + deps. Open a PR from `feature/agent_rag_langgraph` → `feature/rag`.

---

## 12. Acceptance / validation checklist

- [ ] Branch `feature/agent_rag_langgraph` is off `feature/rag`.
- [ ] `generate_answer(question, context)` extracted from `query()`; `query()` delegates to it; **`test_rag.py` unchanged and passing.**
- [ ] `AgentState` is minimal (no unjustified conversation history).
- [ ] Three single-responsibility nodes + a `no_context` node; **no node does retrieve+generate silently.**
- [ ] Two conditional-edge functions with real conditions: empty question → END; no-context-above-threshold → `no_context` ("I don't have information about that.").
- [ ] `query_node` calls `generate_answer`, **never `query()`.**
- [ ] Graph compiled once before serving; structural errors fail at startup; `MemorySaver` checkpointer attached with per-request `thread_id`.
- [ ] Per-run queryable trace (`trace_steps`) returned; LangSmith wired via env and optional at runtime.
- [ ] Agent router mounted on `api_v1_router` at the same level as the knowledge router → `POST /api/v1/agent/query`, coexists with `/api/v1/knowledge/query`, delegates to the graph, returns `{answer, trace_id, sources}`, and returns a clear no-stack-trace message on failure.
- [ ] ≥3 evals in `tests/pipelines/test_agent_evals.py`, asserting against the trace; ≥1 grounding eval that passes (or skips cleanly without a key).
- [ ] `langgraph` + `langsmith` in `pyproject.toml`; `uv.lock` updated; `.example.env` documents `LANGCHAIN_*`.

---

## 13. Suggested additional tasks (to improve model/agent outcomes)

These are recommendations beyond the assignment; implement if time allows or flag for a follow-up.

1. **Record-and-replay grounding fixture.** Capture one real proxy response per grounding question into a JSON fixture so eval 3 runs deterministically in CI without a key. Prevents flaky grounding gates.
2. **LLM-as-judge grounding eval.** In addition to entity-match, add an optional judge pass (reuse the `--judge` path already in `data/eval/run_eval.py`) scoring "is every claim supported by the retrieved context?" — catches subtle hallucination that string-match misses.
3. **Log agent interactions to the existing feedback store.** Mirror `answer_question`'s `feedback_store.append_record` so agent runs are auditable alongside RAG runs (with `redact_pii`), enabling later offline eval on real traffic.
4. **Emit `trace_id` in the response headers and structured logs** so a support agent's answer can be traced back to its LangSmith run.
5. **Add a `retrieved_context` echo (top source titles) to the trace step summaries** — makes the "grounded vs not" story visible in LangSmith without exposing full chunk text.
6. **Guard against near-threshold answers.** Consider a second, stricter conditional: if the top hit's score is only marginally above `rag_min_score`, still answer but tag the trace `low_confidence=true` for eval/monitoring. (Do not change the RAG threshold itself.)
7. **Concurrency note for `MemorySaver`.** It is in-process/in-memory — fine for a single worker. If the API runs multiple Uvicorn workers, document that checkpoints are per-process, and leave a TODO for a `SqliteSaver`/`PostgresSaver` (the repo already has Postgres) if durable cross-worker checkpointing is ever needed.
8. **Streaming variant (stretch).** Expose `compiled_graph.stream(...)` behind a `?stream=true` flag for token/step streaming — useful for the backoffice UI.

---

## 14. Model recommendations for this use case

The app talks to an **OpenAI-compatible proxy** (`https://llm.4geeks.ai`) with OpenRouter-namespaced model ids; the current generation model is `deepseek-v4-flash`. This is a **grounded, low-latency, extractive support-desk** task (short answers strictly from provided context, must not hallucinate coverage/fees), so instruction-following + faithfulness matter more than raw reasoning depth or long context.

- **Keep `deepseek-v4-flash` as the default.** It is cheap and fast, and the answer is already tightly constrained by `SYSTEM_PROMPT` + retrieved context — a good fit for high-volume front-desk traffic.
- **For the grounding-critical / production tier**, prefer a model with strong instruction-following and low hallucination on RAG. If the proxy exposes them via OpenRouter, good candidates (all OpenAI-compatible through the same client, so a drop-in `settings.generation_model` change):
  - **Anthropic Claude Haiku 4.5** — fast, strong at "answer only from context / abstain otherwise," excellent instruction adherence; a strong default upgrade for faithfulness at low latency.
  - **Anthropic Claude Sonnet 4.x** — when answer quality/nuance (US vs UK coverage split, Medicare/Medicaid fee rules) matters more than cost.
  - **A strong open reasoning model** (e.g. the current DeepSeek reasoning line) — good middle ground if you want to stay in-family.
- **Do NOT change the embedding model** unless you re-embed the whole collection — retrieval quality is coupled to the stored vectors (`pplx-embed-v1`). Swapping embeddings requires a full re-`setup()`.
- **Evaluation model:** if you add the LLM-as-judge eval (#2 above), use a stronger model than the answer model as the judge (e.g. Claude Sonnet) so the grader isn't limited by the same blind spots.

> Selection is a `settings.generation_model` string change (validate the exact id the proxy accepts) — no code changes, since generation already flows through the OpenAI-compatible `_generate`. Verify latency/cost against the proxy's actual catalog before switching the default.

---

## 15. Assumptions & open items

- **Agent endpoint sits at the same level as the RAG endpoint** — mounted on `api_v1_router`, so the path is `/api/v1/agent/query` (sibling of `/api/v1/knowledge/query`). — *confirmed.*
- **Authenticated** via the v1 router's `Depends(get_current_user)`, same as the knowledge router. If it should be public, drop that dependency. — *confirmed direction; flag if wrong.*
- **Code lives in `services/api/app/domains/agent/`** (repo convention), not the syllabus guide's `services/agent/` — the guide's layout doesn't exist in this repo. — *confirmed.*
- **In-state `trace_steps` is the eval source of truth; LangSmith is additive.** — *confirmed.*
- Collection is assumed already seeded in dev (`_ensure_knowledge_base()` runs on startup); grounding eval will `setup()` if empty and a key is present.
