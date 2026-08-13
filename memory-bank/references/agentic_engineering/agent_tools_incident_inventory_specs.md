# Spec — Agent Tools: Incident + Inventory (continuation of `feature/agent_rag_langgraph`)

> **Audience:** a coding agent extending the LangGraph support agent.
> **Prerequisite:** Part 1 is implemented — see `agent_rag_langgraph_specs.md`. This spec extends the existing `services/api/app/domains/agent/` package.
> **Branch:** all Part 2 work is done on a **new feature branch `feature/agent_tools_langgraph`, cut off of `feature/agent_rag_langgraph`** (which carries the Part 1 agent). Do **not** create a new endpoint — the tools plug into the existing compiled graph and the existing `POST /api/v1/agent/query`.

---

## 1. Project overview

Part 1 turned the RAG knowledge assistant into a compiled, checkpointed LangGraph graph exposed at `POST /api/v1/agent/query`. Part 2 makes it a **multi-source agent**: besides answering from the knowledge base (RAG), it can answer operational questions by calling two live HTTP APIs already in this backend:

- **Incident system** — ticket status/details.
- **Inventory manager** — medical-supply products and current stock.

The agent must decide **from the question** whether to answer via RAG, via a tool, or via both, call the chosen source(s) over HTTP with explicit timeouts, degrade honestly when a service fails or returns nothing, and record in each run's trace which sources were used.

### Behavioral contract (what "done" looks like)
- "Do you take Medicaid?" → **RAG only**.
- "What's the status of incident 42?" → **incident tool only**.
- "How many surgical masks do we have in stock?" → **inventory tool only**.
- "What's our mask policy and do we have any in stock?" → **RAG + inventory tool (both)**.
- Incident/inventory service times out, errors, or returns no data → the agent answers honestly with the mandated fallback string (§6) — it never fabricates a status.
- Every run's trace shows exactly which sources ran (`rag`, `incident_tool`, `inventory_tool`).

---

## 2. Locked design decisions (from clarifying questions)

1. **Transport & auth:** tools call the API over **HTTP (httpx)** to a configurable base URL with **explicit per-call timeouts**. The **end-user's bearer token** from the `/agent/query` request is threaded into graph state and **forwarded** on the incidents call. (Inventory's list route is public but the token is forwarded harmlessly.)
2. **Routing:** an **LLM intent-classifier node** emits structured multi-label intent (handles "both"). Evals stub it for determinism.
3. **Answer on tool success:** **LLM-composed, grounded strictly in the tool's returned JSON** (blended with RAG context when both ran).
4. **Identifiers:** **extracted from the free-text question** by the classifier. The `/agent/query` request keeps its single `question` field — no schema change. Inventory has no server-side name filter, so the tool fetches all products and matches by name/SKU in-agent.

---

## 3. Tech stack (delta from Part 1)

Unchanged base (Python ≥3.12, `uv`, FastAPI, LangGraph, LangSmith, Qdrant, OpenAI-compatible proxy at `settings.llm_base_url`). New in Part 2:

| Concern | Choice | Notes |
|---|---|---|
| Tool HTTP client | **`httpx`** (already a dependency) | sync `httpx.Client` with `httpx.Timeout`; no new package |
| Intent classification | LLM via existing `_generate`-style proxy call, **JSON output** | reuse the proxy; add a dedicated classifier prompt |
| Typed contracts | **Pydantic models** (already present) | tool inputs/outputs |
| New settings | `internal_api_base_url`, `tool_http_timeout_seconds` | `services/api/app/core/config.py` |

No new third-party dependency is required.

---

## 4. Real API contracts the tools call (verified on `origin/feature/rag`)

> The task wrote the paths approximately (`/api/incidents`, `/inventory/products`). In this repo every domain sits under the `/api/v1` prefix, so the real paths are:

**Incident system** — `services/api/app/domains/incidents/router.py`, mounted with `Depends(get_current_user)` (**auth required**):
- `GET /api/v1/incidents` → `list[IncidentRead]`; optional query params `status`, `origin`, `branch`, `category`.
- `GET /api/v1/incidents/{incident_pk}` → `IncidentRead`; `404` if not found.
- `IncidentRead`: `id:int, title:str, description:str, category:str, status:str, origin:str, branch:str, created_at:datetime, updated_at:datetime`.

**Inventory manager** — `services/api/app/domains/inventory/router.py`, list route is **public** (no auth dependency):
- `GET /api/v1/inventory/products` → `list[MedicalSupplyRead]` (returns **all** products; no name filter).
- `MedicalSupplyRead`: `id:int, name:str, sku:str, category:str, unit:str, country:str, current_stock:int`.

---

## 5. Typed tool contracts (`app/domains/agent/tools/`)

New subpackage `app/domains/agent/tools/` with a shared HTTP helper and one module per tool. **Both tools have an explicit typed input and typed output. Tool functions NEVER raise to the graph — they return a typed result with `ok=False` on any failure (this is the recovery contract).**

```python
# tools/base.py
from __future__ import annotations
import httpx
from app.core.config import settings

def tool_timeout() -> httpx.Timeout:
    t = settings.tool_http_timeout_seconds  # default 5.0
    return httpx.Timeout(t, connect=min(t, 3.0))

def api_url(path: str) -> str:
    return f"{settings.internal_api_base_url.rstrip('/')}{path}"  # base e.g. http://localhost:8000
```

### 5.1 Incident tool
```python
# tools/incident.py
from pydantic import BaseModel
from typing import Any, Literal

class IncidentToolInput(BaseModel):
    incident_id: int | None = None            # extracted from question; None -> list mode
    status: str | None = None                 # optional filters (list mode)
    origin: str | None = None
    branch: str | None = None
    category: str | None = None

class IncidentToolResult(BaseModel):
    source: Literal["incident_tool"] = "incident_tool"
    ok: bool
    incident: dict[str, Any] | None = None    # single IncidentRead (by-id mode)
    incidents: list[dict[str, Any]] = []      # list mode
    error: str | None = None                  # "timeout" | "http_502" | "not_found" | "unauthenticated" | "transport"
    empty: bool = False                       # ok but no data returned

def run_incident_tool(inp: IncidentToolInput, *, auth_token: str | None) -> IncidentToolResult: ...
```
Behavior:
- Requires `auth_token`. If missing → `ok=False, error="unauthenticated"`.
- If `incident_id` is set → `GET /api/v1/incidents/{incident_id}`. `404` → `ok=False, error="not_found"`.
- Else → `GET /api/v1/incidents` with the provided filters as query params.
- Header: `Authorization: Bearer <auth_token>` (forwarded). Timeout: `tool_timeout()`.
- `httpx.TimeoutException` → `ok=False, error="timeout"`. Other `TransportError` → `error="transport"`. Non-2xx → `error=f"http_{status}"`.
- `ok=True` but empty list / null → `empty=True`.

### 5.2 Inventory tool
```python
# tools/inventory.py
class InventoryToolInput(BaseModel):
    name_hint: str | None = None              # extracted product name/keyword; matched in-agent

class InventoryToolResult(BaseModel):
    source: Literal["inventory_tool"] = "inventory_tool"
    ok: bool
    products: list[dict[str, Any]] = []       # all products (or filtered by name_hint)
    matched: list[dict[str, Any]] = []        # subset matching name_hint (case-insensitive on name/sku)
    error: str | None = None
    empty: bool = False

def run_inventory_tool(inp: InventoryToolInput, *, auth_token: str | None) -> InventoryToolResult: ...
```
Behavior:
- `GET /api/v1/inventory/products` (public; forward token anyway). Timeout + error mapping identical to the incident tool.
- If `name_hint` present, compute `matched` by case-insensitive substring match on `name` and `sku`; keep `products` too.
- `ok=True` with `products == []` (or `name_hint` set and `matched == []`) → `empty=True`.

---

## 6. Mandated honest fallbacks (verbatim)

These exact strings must be emitted **deterministically** (not paraphrased by the LLM) whenever the corresponding tool fails (`ok=False`) or returns no data (`empty=True`):

```python
INCIDENT_FALLBACK  = "I could not confirm the ticket's status."
INVENTORY_FALLBACK = "I could not confirm the inventory item's status."
```
- If a tool was the **only** requested source and it failed/empty → the answer is exactly that string (see the explicit recovery node, §7.4).
- If a tool failed but **another** source (e.g. RAG or the other tool) succeeded → the verbatim fallback line is appended deterministically to the composed answer; the LLM only composes over the sources that returned real data.

---

## 7. Graph changes

Extend the Part 1 graph. New nodes: **`classify`**, **`incident_tool`**, **`inventory_tool`**, a barrier **`gather`**, and an explicit recovery node **`honest_fallback`**. The Part 1 RAG generation node is generalized into a single **`compose`** node that grounds an answer over whatever sources returned data.

### 7.1 State additions (`state.py`)
```python
class AgentState(TypedDict):
    question: str
    normalized_question: str | None
    auth_token: str | None                                  # forwarded bearer, for tool calls
    intent: dict | None                                     # classifier output (see 7.2)
    retrieved_context: list[dict] | None                    # RAG hits
    incident_result: dict | None                            # IncidentToolResult.model_dump()
    inventory_result: dict | None                           # InventoryToolResult.model_dump()
    answer: str | None
    sources: list[dict] | None                              # RAG sources for endpoint parity
    sources_used: Annotated[list[str], operator.add]        # {"rag","incident_tool","inventory_tool"} — trace signal
    trace_id: str
    trace_steps: Annotated[Sequence[dict], operator.add]
    error: str | None
```
> `retrieved_context`, `incident_result`, `inventory_result` are **distinct keys**, so parallel tool/RAG branches write without conflict. `sources_used` and `trace_steps` use `operator.add` reducers so concurrent branches accumulate safely.

### 7.2 `classify` node (LLM intent classifier)
Calls the proxy with a strict JSON-output prompt. Returns and stores:
```json
{
  "use_rag": true,
  "use_incident": false,
  "use_inventory": false,
  "incident_id": null,
  "product_hint": null,
  "reasoning": "…"
}
```
Rules:
- The prompt lists the three capabilities and instructs the model to select **one or more**, extract an `incident_id` (integer) if the question names a ticket, and a `product_hint` (short noun phrase) for inventory.
- **Deterministic parse + safe default:** if the response is unparseable or selects nothing, default to `{use_rag: true}` and log a warning. Never crash.
- Appends a `classify` trace step summarizing the chosen route.
- Injectable seam for evals: `classify` uses a module-level `classifier_fn` (default = real LLM call) that tests can monkeypatch to return a fixed intent.

### 7.3 Routing (`routing.py`)
```python
def after_receive(state) -> str:            # from Part 1, unchanged
    return "classify" if state.get("normalized_question") else "end"

def route_intent(state) -> list[str]:       # FAN-OUT conditional edge (REAL condition on intent)
    intent = state["intent"]
    targets = []
    if intent.get("use_incident"):  targets.append("incident_tool")
    if intent.get("use_inventory"): targets.append("inventory_tool")
    if intent.get("use_rag") or not targets: targets.append("retrieve")  # RAG is the safe default
    return targets

def after_gather(state) -> str:             # EXPLICIT RECOVERY decision
    rag_ok       = bool(state.get("retrieved_context"))
    inc          = state.get("incident_result")
    inv          = state.get("inventory_result")
    inc_ok       = bool(inc) and inc["ok"] and not inc["empty"]
    inv_ok       = bool(inv) and inv["ok"] and not inv["empty"]
    tool_requested = inc is not None or inv is not None
    if not rag_ok and not inc_ok and not inv_ok:
        return "honest_fallback"            # every requested source failed/empty -> explicit recovery
    return "compose"
```

### 7.4 Nodes & edges
- **`incident_tool`** — build `IncidentToolInput` from `intent`, call `run_incident_tool(..., auth_token=state["auth_token"])`, store `incident_result`, append `sources_used += ["incident_tool"]`, and a trace step with `output_summary` including `ok`/`error`/`empty`.
- **`inventory_tool`** — same pattern with `run_inventory_tool`; `sources_used += ["inventory_tool"]`.
- **`retrieve`** — reused from Part 1; on success append `sources_used += ["rag"]`.
- **`gather`** — barrier no-op node that all three source nodes point to; lets LangGraph join the parallel branches before deciding. Appends a `gather` trace step listing `sources_used`.
- **`compose`** — the single grounded-generation node:
  - Assemble a combined context: RAG chunks (via `build_assembled_prompt`-style blocks) **+** the successful tool JSON (labeled `[INCIDENT SYSTEM]` / `[INVENTORY]`).
  - Call the LLM (reuse `generate_answer`'s generation path / `_generate`) to produce a natural-language answer grounded **only** in that combined context.
  - **Deterministically append** the verbatim §6 fallback line for any tool that was requested but failed/empty.
  - Set `sources` (RAG parity) and `answer`.
- **`honest_fallback`** — explicit recovery node (no LLM). Emits the verbatim §6 string(s) for the failed/empty tool(s); if RAG was the sole source and returned nothing, emit the Part 1 RAG no-context message. This node is the graph's **explicit recovery path**.

Edges:
```
set_entry_point("receive_question")
receive_question --after_receive--> {classify, END}
classify --route_intent(list)--> {retrieve, incident_tool, inventory_tool}   # fan-out
retrieve      --> gather
incident_tool --> gather
inventory_tool--> gather
gather --after_gather--> {compose, honest_fallback}
compose --> END
honest_fallback --> END
```
Recompile at import with the existing `MemorySaver` checkpointer; compilation must still fail loudly on structural errors.

### 7.5 Timeouts & recovery (explicit)
- Every tool HTTP call uses `settings.tool_http_timeout_seconds` (default **5.0s**) via `httpx.Timeout`.
- Tools **catch all** `httpx` timeout/transport errors and non-2xx responses and return `ok=False` — they never propagate exceptions into the graph.
- The **explicit recovery path** is the `after_gather` conditional edge → `honest_fallback` node (all sources failed) plus `compose`'s deterministic per-source fallback lines (partial failure).

---

## 8. Endpoint wiring (no contract change)

`POST /api/v1/agent/query` request/response shape is unchanged. Two internal changes:
- `router.py`: read the raw bearer token from the incoming request (`Authorization` header) and pass it to the service.
- `service.invoke_graph(question, *, auth_token)`: seed `auth_token` into the initial state so tool nodes can forward it. Never log the token.
- Response may additionally include `sources_used` (helpful, optional) so callers/evals can see routing. Keep `{answer, trace_id, sources}` intact.

New settings in `config.py`:
```python
internal_api_base_url: str = "http://localhost:8000"   # where this API is reachable for tool calls
tool_http_timeout_seconds: float = 5.0
```
Document both in `services/api/.example.env`.

---

## 9. Tracing — each run shows RAG vs tool

- `sources_used` accumulates the exact set of sources that executed; the `compose`/`honest_fallback` trace step echoes it.
- Every node still appends a `trace_step` (Part 1 in-state trace = eval source of truth).
- LangSmith (Part 1 env wiring) captures the same run; the fan-out branches appear as parallel nodes.

---

## 10. Evals — 2 NEW routing evals (`tests/pipelines/test_agent_evals.py`)

Add to the Part 1 eval file. **Assert against the trace** (`sources_used` / `trace_steps`), consistent with Part 1. Stub the `classifier_fn` and the tool HTTP client for determinism; stub the compose LLM where the assertion is about routing, not wording.

| # | Name | Input | Setup (stubs) | Asserts against trace |
|---|---|---|---|---|
| 4 | **Resolves with the TOOL** | "What is the status of incident 42?" | `classifier_fn` → `{use_incident:true, incident_id:42}`; incident HTTP stub → a fixture `IncidentRead` (`status:"in_progress"`) | `sources_used == ["incident_tool"]`; **no `"rag"`**; trace shows `classify → incident_tool → gather → compose`; answer contains the incident's status |
| 5 | **Resolves with RAG** | "Do you take Medicaid in the US?" | `classifier_fn` → `{use_rag:true}`; tool HTTP stubs asserted **not called** | `sources_used == ["rag"]`; no `incident_tool`/`inventory_tool` step; trace shows `classify → retrieve → gather → compose` |

Existing Part 1 evals stay; **update only Part 1's node-order assertion** to a *subsequence* check (`retrieve` precedes `compose`) since `classify` is now inserted before `retrieve` and `query` was generalized to `compose`. The grounding acceptance-gate eval and the empty-question eval remain valid.

> These agent evals are in addition to the RAG tests. `tests/pipelines/test_rag.py` and `services/api/tests/test_knowledge.py` must still pass unchanged.

---

## 11. Constraints & guardrails

- **Reuse Part 1** nodes/graph/tracing; do not fork the package or the endpoint. Work on `feature/agent_tools_langgraph` (branched off `feature/agent_rag_langgraph`); open the PR back into `feature/agent_rag_langgraph`.
- **Tools use the HTTP API** with explicit timeouts; they **never raise** into the graph (recovery contract).
- **Honest fallback strings are verbatim and deterministic** — never LLM-generated/paraphrased.
- **Forwarded JWT is never logged**; redact incident `description`/PII if any tool payload is logged (reuse `redact_pii`).
- The RAG-only path must remain behaviorally identical to Part 1 (same answers, same grounding).
- Classifier must fail safe to RAG; a classifier outage must not break answering knowledge questions.
- Compose grounds **only** in returned data; if a tool returned nothing, its facts must not appear — only the honest line.
- Match existing style (`from __future__ import annotations`, typed, module `logger`, Pydantic models).

---

## 12. Dependencies

- **No new packages** (httpx, pydantic, langgraph, langsmith already present). Verify `httpx` is in `services/api/pyproject.toml` dependencies (it is).
- New env keys: `INTERNAL_API_BASE_URL`, `TOOL_HTTP_TIMEOUT_SECONDS` (+ existing `LANGCHAIN_*` from Part 1). Add to `.example.env`.

---

## 13. Development workflow

```bash
# Cut a new feature branch off feature/agent_rag_langgraph (which has Part 1)
git fetch origin
git checkout -b feature/agent_tools_langgraph origin/feature/agent_rag_langgraph

# 1. Add settings (internal_api_base_url, tool_http_timeout_seconds) + .example.env keys
# 2. tools/base.py, tools/incident.py, tools/inventory.py (typed contracts, no-raise)
# 3. classify node + classifier prompt (JSON output, safe default, injectable seam)
# 4. incident_tool / inventory_tool / gather / honest_fallback nodes; generalize query -> compose
# 5. routing.py: route_intent (fan-out) + after_gather (recovery); rewire edges; recompile
# 6. router/service: forward Authorization header into state.auth_token

# Guardrails first, then new evals
uv run pytest tests/pipelines/test_rag.py services/api/tests/test_knowledge.py -q     # must stay green
uv run pytest tests/pipelines/test_agent_evals.py -q                                   # P1 (updated) + new evals 4,5

# Live smoke test (needs the API running so tools can reach it over HTTP)
uv run uvicorn app.main:app --reload
#   POST /api/v1/agent/query  {"question":"status of incident 1?"}      -> incident_tool
#   POST /api/v1/agent/query  {"question":"do you take Medicaid?"}       -> rag
#   POST /api/v1/agent/query  {"question":"mask policy and stock?"}      -> both
#   (stop the API mid-request or set a tiny timeout to see the honest fallback)
```

Commit granularly: (a) settings+contracts, (b) tools, (c) classify+routing, (d) compose+recovery, (e) endpoint token forwarding, (f) evals.

---

## 14. Acceptance / validation checklist

- [ ] Work is on `feature/agent_tools_langgraph`, branched off `feature/agent_rag_langgraph`.
- [ ] Two typed tool contracts (`IncidentToolInput/Result`, `InventoryToolInput/Result`); tools call the real HTTP API and never raise.
- [ ] One graph node per tool (`incident_tool`, `inventory_tool`) plus an LLM `classify` node.
- [ ] `route_intent` conditional edge selects RAG / tool / **both** from the question; `after_gather` is the explicit recovery decision.
- [ ] Explicit per-call **timeouts**; failures/empties handled without crashing the graph.
- [ ] Verbatim honest fallbacks on tool failure/no-data (`I could not confirm the ticket's status.` / `…inventory item's status.`).
- [ ] Each run's trace shows the sources used (`sources_used` + trace steps).
- [ ] Caller JWT forwarded to the incidents call; never logged.
- [ ] 2 new routing evals (one resolves via tool, one via RAG) asserting against the trace; Part 1 node-order eval updated to a subsequence check.
- [ ] RAG tests + knowledge endpoint tests still green; RAG-only behavior unchanged.
- [ ] Graph recompiles at startup; `MemorySaver` still attached; endpoint contract unchanged.

---

## 15. Suggested additional tasks (improve model/agent outcomes)

1. **Add a "both" eval** — a question that must trigger RAG + inventory; assert `sources_used` contains both and the composed answer blends policy + live stock.
2. **Add a tool-failure eval** — stub the incident HTTP call to time out; assert the answer is exactly `INCIDENT_FALLBACK` and the trace records `error="timeout"` and the `honest_fallback` (or deterministic append) path.
3. **Classifier confidence + clarify path** — when intent is ambiguous/low-confidence, route to a `clarify` node that asks a one-line follow-up instead of guessing. Improves precision on vague questions.
4. **Retry-once with backoff on 5xx/timeout** — mirror the RAG `_generate` single-retry pattern in `tools/base.py` before giving up (still bounded by the timeout). Reduces spurious fallbacks.
5. **Cache the product list per request** — inventory returns all products; memoize within a run so a "both" query doesn't fetch twice.
6. **Structured classifier output via JSON schema / function schema** — if the proxy supports response-format JSON, enforce it to eliminate parse failures.
7. **Log tool telemetry** to the existing feedback/interaction store (source, latency, ok/error) for offline routing-accuracy evals on real traffic.
8. **Contract tests for the tools** against a spun-up API (or `respx`-mocked httpx) so schema drift in `IncidentRead`/`MedicalSupplyRead` is caught in CI.
9. **Guard against prompt-injection via tool data** — treat incident `description`/product fields as untrusted; the compose prompt must state that tool data is data, not instructions.

---

## 16. Model recommendations for this use case

Two distinct LLM jobs now exist; they can use different models (both are just `settings.*_model` strings through the OpenAI-compatible proxy).

**Intent classifier (`classify`)** — needs fast, cheap, reliable **structured JSON + entity extraction**, not deep reasoning:
- **Claude Haiku 4.5** — excellent instruction-following and JSON adherence at low latency/cost; strong default for the router.
- **`deepseek-v4-flash` (current)** — fine and cheapest if it reliably returns valid JSON; enforce a strict prompt + parse-with-fallback.
- Whatever the choice, keep temperature ~0 for deterministic routing.

**Answer composition (`compose`)** — grounding faithfulness over RAG + tool JSON matters most:
- **Claude Haiku 4.5** — good faithfulness at low latency; strong default upgrade over the current model for "answer only from provided data / append honest line otherwise".
- **Claude Sonnet 4.x** — when blended "both" answers (policy + live data with US/UK splits) need more nuance; use for a quality tier.

**If you later switch routing to native tool-calling** (§ suggested task), prefer a model with first-class function-calling — **Claude Sonnet 4.x** — and verify the 4geeks proxy exposes tool-calling for it before committing; deepseek tool-calling through the proxy is unverified.

Do **not** change the embedding model (retrieval vectors are coupled to `pplx-embed-v1`). Model selection here is a settings string change only — no code changes, since both jobs flow through the existing proxy client.

---

## 17. Assumptions & open items

- Tools reach this same API over HTTP at `internal_api_base_url` (default `http://localhost:8000`); in Docker/compose set it to the API service URL. — *confirm the deployed base URL.*
- The incident tool authenticates with the **caller's** forwarded JWT; if a future non-interactive caller has no token, incident answers degrade to the honest fallback. — *confirmed direction.*
- The task's `GET /api/incidents` / `GET /inventory/products` map to `/api/v1/incidents` and `/api/v1/inventory/products` in this repo. — *confirmed from the routers.*
- "Incident id" and "product" identifiers are extracted from the free-text `question`; the endpoint contract is unchanged. — *confirmed.*
- Generalizing Part 1's `query` node into `compose` requires updating Part 1's node-order eval to a subsequence assertion. — *intended; called out in §10.*
