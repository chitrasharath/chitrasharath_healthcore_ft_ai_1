# SPEC — RFP Intake, Phase 1 (Milestone 9, Part 1)

> **Audience:** the coding agent implementing this feature.
> **Source of truth for domain rules:** [`CONTEXT-multi_agent.md`](./CONTEXT-multi_agent.md) — read it in full first. This spec operationalizes **Part 1 only**.
> **Repo:** `chitrasharath_healthcore_ft_ai_1/` (the HealthCore monorepo).
> **Base branch:** `feature/agent_memory` → **new work branch:** `feature/rfp-intake`.

---

## 1. Project Overview

HealthCore responds to institutional B2B RFPs (occupational health, corporate wellness, referral partnerships) that today take ~3 weeks to turn into a proposal via manual email coordination between Revenue Cycle, Clinical Operations, and Compliance. Milestone 9 replaces that with an agentic, multi-department workflow across **three parts**. **This spec implements Part 1 (intake) only.** Parts 2 (section generation + evaluation) and 3 (per-department approval + arbitration + final document) are explicitly **out of scope** but must not be architecturally precluded — the same `Ticket` row and `DepartmentSection` rows are reused across all three parts.

**Phase 1 goal:** an authenticated user uploads a PDF RFP through the backoffice, a `Ticket` is created, the `rfp_intake` pipeline converts + analyzes the document, a **classifier agent** decides whether it is a genuine HealthCore RFP (discard if not), and for valid RFPs an **orchestrator → worker → synthesizer** multi-agent produces per-department `key_aspects` plus a sales-facing summary. On success the ticket reaches `intake_complete`.

### 1.1 End-to-end flow (Phase 1)

```
[uis/backoffice upload PDF]
        │  POST multipart → services/api
        ▼
[create Ticket status=analyzing] ──> [store PDF under data/raw/] ──> [enqueue JobRun]
        │  (FastAPI BackgroundTask picks up the JobRun)
        ▼
[data/pipelines/rfp_intake graph]
   1. convert PDF → markdown            (markitdown)
   2. PHI scan / redact                 (reuse existing detectors)   ── PHI? → flag contains_phi, block raw content
   3. extract RFP metadata              (LLM, structured)
   4. readability metrics               (py-readability-metrics)
   5. persist RFP metadata + metrics on the Ticket
        ▼
[classifier-agent] ── not an RFP ──> Ticket status=discarded  (STOP)
        │ valid RFP
        ▼
[orchestrator] decompose → departments_needed (revenue, clinical, compliance*)
        ▼
[workers ×N]  each: metadata + department-relevant extracts → DepartmentSection.key_aspects
        ▼
[synthesizer] consolidate worker outputs → sales-facing summary ("what to ask whom")
        ▼
[Ticket status=intake_complete]
```
`*` `compliance` is **mandatory on every valid RFP** regardless of content (CONTEXT §2.1).

---

## 2. Tech Stack (use what already exists — do not introduce parallel stacks)

| Layer | Technology | Where it lives today |
| --- | --- | --- |
| Backend API | FastAPI + SQLModel, domain-per-folder | `services/api/app/domains/*`, routers wired in `services/api/app/api/v1/router.py` |
| DB (source of truth) | PostgreSQL via **Supabase**, SQLModel `table=True` models, `create_engine` on `settings.database_url` | `services/api/app/core/db.py` (`supabase_engine`), models e.g. `app/domains/telemetry/reporting_models.py` |
| Pipelines / graphs | Prefect flows + extract/transform/load task modules | `data/pipelines/` (`pipeline.py`, `config.py`, `extract/`, `transform/`, `load/`) |
| Multi-agent graph | **LangGraph** (`StateGraph`, `MemorySaver`, typed-dict state, node + conditional-edge routing) | `services/api/app/domains/agent/{graph,state,nodes,routing}.py` |
| LLM access | OpenAI-compatible chat-completions proxy (`llm.4geeks.ai`), Bearer `settings.llm_api_key`, model `settings.generation_model` | pattern in `app/domains/agent/nodes.py::_call_classifier_llm` |
| Job / run state machine | `JobRun` SQLModel + `job_runner.py` helpers (pending → processing → completed/failed, stale-lock reclaim) | `app/domains/jobs/` |
| Frontend | Next.js (App Router, TS) backoffice apps | `uis/backoffice/*` (mirror the `knowledge` app’s components/hooks/lib layout) |
| PHI/PII detection (reuse) | `detect_phi`, `redact_pii`, `validate_no_phi`, pipeline tag scanner | see §6 |
| Tests | pytest from repo root; pipeline tests in `tests/pipelines/` | `tests/pipelines/test_pipeline.py` for conventions |

**LLM call convention (copy this — do not add `langchain-anthropic`/`openai` SDKs):** POST to `{settings.llm_base_url}/v1/chat/completions` with `{"model": settings.generation_model, "temperature": 0, "messages": [...]}`, `Authorization: Bearer {settings.llm_api_key}`, via `httpx.Client`. When `settings.llm_api_key` is unset, **fail safe** (see §7 per node). Parse structured output with the fenced-JSON extraction pattern already in `nodes.py::_parse_intent_json`.

---

## 3. Availability Verification — `data/pipelines` & supporting infra

Confirmed present on `feature/agent_memory` (base branch) and **reusable as-is**:

| Need | Status | Reference |
| --- | --- | --- |
| Pipeline scaffolding (extract/transform/load, Prefect `@flow`) | ✅ present | `data/pipelines/pipeline.py`, `data/pipelines/config.py` |
| Run-state machine with checkpoints + failure/quarantine handling | ✅ present | `pipeline.py` (`start_run`/`finish_run`/`load_run`, `checkpoint` field), `data/pipelines/load/runs.py` |
| Job lifecycle table + helpers (pending→processing→completed/failed, stale reclaim, idempotency guards) | ✅ present | `app/domains/jobs/models.py` (`JobRun`), `job_runner.py` |
| Supabase engine + SQLModel table pattern + `SQLModel.metadata.create_all` | ✅ present | `app/core/db.py`, `reporting_models.py` |
| `sys.path` bootstrap so `data.pipelines.*` can import `app.*` | ✅ present | top of `pipeline.py` (parents[2] + `services/api`) |
| PHI detectors to reuse | ✅ present | `data/pipelines/extract/phi.py`, `app/domains/agent/harness/input_guards.py::detect_phi`, `app/domains/knowledge/pii.py::redact_pii`, `app/domains/agent/memory/phi.py::validate_no_phi` |
| LangGraph patterns (state, nodes, conditional routing, compile) | ✅ present | `app/domains/agent/graph.py` |
| LLM proxy config | ✅ present | `app/core/config.py` (`llm_base_url`, `llm_api_key`, `generation_model`) |
| Backoffice Next.js app template | ✅ present | `uis/backoffice/knowledge/` |
| `tests/pipelines/` with conventions | ✅ present | `tests/pipelines/test_pipeline.py` |
| `data/raw/` directory for uploaded artifacts | ✅ present (has README only) | `data/raw/` |

**Missing — the coding agent MUST add these (they do not exist on the base branch):**

1. **`markitdown`** — not in `uv.lock`/`pyproject`. Add to `services/api/pyproject.toml` deps and `uv lock`.
2. **`py-readability-metrics`** — not present. Add likewise. (Import name is `readability`; it depends on an NLTK `punkt` download — see §5.4 for the offline/vendored handling requirement.)
3. **`data/pipelines/rfp_intake/`** — new package, does not exist.
4. **`rfp-requests/healthcore/` seed PDFs** — referenced by CONTEXT §4 but **not present in the repo**. Treat as test inputs to be supplied at runtime through the UI. The coding agent must (a) not assume they exist as committed fixtures, and (b) create the **PHI critical-case PDF** itself (CONTEXT §4.4) as a test artifact. See §9.
5. **No file-upload (multipart) endpoint exists yet** — the `knowledge` and `agent` routers are JSON-only. The upload route is net-new; follow the FastAPI `UploadFile` pattern.

> Deliver a short "availability check" note in the PR description confirming items 1–5 were addressed.

---

## 4. Constraints (non-negotiable)

1. **HIPAA / UK GDPR — no PHI anywhere.** No patient identifier or PHI may appear in any event, table, endpoint, log, ticket, file path, or generated document — **not even as an illustrative example** (CONTEXT §0, §2.3, §5). This is the single highest-priority constraint; when in doubt, block and flag.
2. **Supabase is the source of truth** for `Ticket`, `RFP metadata`, and `DepartmentSection`. TinyDB/JSON files are **not** acceptable for these entities (CONTEXT §2.3). Use the existing SQLModel/`supabase_engine` layer.
3. **Monorepo layout** (CONTEXT §2.4): extend the **existing** backend under `services/` (no new API process); pipeline/graph lives in `data/pipelines/rfp_intake/` (do **not** mix into the CX agent graph in `app/domains/agent/graph.py`); routers only import & trigger, they don’t own agent logic; uploaded PDFs stored under `data/raw/` as runtime artifacts (no PHI in filenames).
4. **Never invent data.** If covered-population/volume/budget figures are missing, record **open questions**, never fabricate headcount, budget, or PHI (CONTEXT §2.3, §5).
5. **Status vocabulary is fixed** (CONTEXT §2.3): use `analyzing`, `discarded`, `intake_complete` (underscores). Do not use hyphenated variants.
6. **Reuse, don’t reinvent** the PHI detectors, job-run state machine, and LLM-proxy call convention listed above.

---

## 5. Detailed Requirements

### 5.1 Backoffice upload UI — `uis/backoffice/rfp-intake/` (new app, mirror `knowledge/`)

- App-router page with a **PDF upload** control (accept `application/pdf` only, client-side guard on type + a sane max size, e.g. 20 MB). Mirror the `knowledge` app’s `components/ hooks/ lib/ types/` structure and its `lib/*-api.ts` fetch helper (forward the existing auth token exactly as `knowledge-api.ts` does).
- On submit: `POST` multipart to the new upload endpoint; on `202` show the returned `ticket_id` and status `analyzing`.
- **Ticket list / detail view:** show tickets with `status`, `client_name`, `program_type`, `departments_needed`, readability summary, and — when `intake_complete` — the per-department `key_aspects` and the synthesizer’s sales-facing summary. When `discarded`, show the classifier’s reason. When `contains_phi` was flagged, show a compliance-review banner and **never render raw extracted PHI** (show redacted preview only).
- Poll ticket status (simple interval or manual refresh) so the user sees `analyzing → intake_complete/discarded`.
- Follow `AGENTS.md` §2: read applicable `.agents/rules/frontend/*` before writing UI.

### 5.2 Upload endpoint + Ticket creation — `services/api/app/domains/rfp_intake/`

New domain folder (`router.py`, `service.py`, `models.py`, `schemas.py`, `__init__.py`). Wire the router into `app/api/v1/router.py` **behind `Depends(get_current_user)`** (match `knowledge_router`/`agent_router`).

Endpoint behavior (`POST /api/v1/rfp-intake/uploads`, `UploadFile`):
1. Validate content type is PDF; reject otherwise (`415`/`400`).
2. Create `Ticket` row: `status="analyzing"`, generate `rfp_id`, `created_at`.
3. Persist the PDF under `data/raw/` using a **non-PHI filename** (e.g. `data/raw/{ticket_id}.pdf`); set `raw_pdf_path`.
4. Create a `JobRun` (`job_name="rfp_intake"`, target keyed by ticket) via `job_runner.create_pending`; enqueue processing through **FastAPI `BackgroundTasks`** (chosen run model — see §8.5).
5. Return `202 Accepted` with `{ ticket_id, rfp_id, status }`. Never block the request on pipeline completion.

Additional read endpoints: `GET /api/v1/rfp-intake/tickets`, `GET /api/v1/rfp-intake/tickets/{ticket_id}` (returns ticket + metadata + department key_aspects + summary; redacted only).

### 5.3 `rfp_intake` pipeline — `data/pipelines/rfp_intake/`

New package parallel to the telemetry pipeline. Do **not** modify `data/pipelines/pipeline.py`; reuse its conventions (sys.path bootstrap, `_ensure_engine`, checkpoint updates, try/except → mark run failed). Suggested modules:

```
data/pipelines/rfp_intake/
  __init__.py
  graph.py          # LangGraph StateGraph for intake (convert→phi→extract→metrics→classify→orchestrate→work→synthesize)
  state.py          # RfpIntakeState TypedDict
  runner.py         # entrypoint invoked by the BackgroundTask + a __main__ CLI for local runs
  convert.py        # markitdown PDF→markdown
  metadata.py       # LLM structured metadata extraction
  readability.py    # py-readability-metrics wrapper
  phi.py            # thin adapter over existing detectors (see §6)
  agents/
    classifier.py   # classifier-agent node
    orchestrator.py # decompose → departments_needed
    worker.py       # per-department key_aspects
    synthesizer.py  # sales-facing summary
  repository.py     # Supabase upserts for Ticket / RfpMetadata / DepartmentSection
```

**Ordered steps (each a graph node; update `JobRun`/checkpoint after each so a mid-way failure is diagnosable — see §8.5):**

1. **Convert** (`convert.py`): `markitdown` PDF → markdown. Store the markdown (e.g. `data/raw/{ticket_id}.md` or a DB text column — pick one and document it).
2. **PHI scan** (`phi.py`): scan markdown; if PHI detected, set `DepartmentSection.evaluation_results.contains_phi=true` semantics on the ticket/section and **redact** before any content is passed downstream or stored. Raw PHI must never reach worker prompts, logs, the ticket UI, or DB text columns. (See §6, §8.1.)
3. **Extract metadata** (`metadata.py`): LLM structured extraction of `client_name`, `client_country` (US/UK), `program_type`, `covered_population`, `deadline`, `budget_range`. Missing values → `open_questions`, never invented (§4.4).
4. **Readability** (`readability.py`): compute metrics with `py-readability-metrics` (e.g. Flesch Reading Ease, Flesch-Kincaid grade, SMOG, Gunning Fog); store as a JSON column on RFP metadata.
5. **Persist** metadata + metrics on the Ticket via `repository.py` (Supabase).
6. **Classify** → §5.5. If invalid → `status=discarded`, stop.
7. **Orchestrate → work → synthesize** → §5.6. On success → `status=intake_complete`.

### 5.4 `py-readability-metrics` operational note

The library tokenizes via NLTK and may attempt a `punkt` download at runtime. In a sandboxed/offline CI this fails. The coding agent must ensure tokenizer data is available deterministically (vendor/download `punkt` at build time, or guard the metric computation so a tokenizer failure degrades gracefully to `readability_metrics: {status: "unavailable"}` **without failing the whole job**). Document the chosen approach.

### 5.5 `classifier-agent`

- Reads the (redacted) markdown and decides: **is this a genuine HealthCore institutional RFP** (occupational health / corporate wellness / referral partnership request from a prospective institutional client), or **not** (e.g. a vendor pitch such as an EHR sales deck — CONTEXT §4.3)?
- LLM call returns structured `{ is_rfp: bool, confidence: float, reason: str }`. Use temperature 0 and the fenced-JSON parse pattern.
- **Invalid → `status=discarded`**, persist the reason, stop the graph (no orchestrator run).
- Must accept **both formal and informal** RFPs (CONTEXT §4.1–4.2: a formal PDF *and* an email-style request are both valid).
- **Invalid-RFP definition (design decision #3)** — see §8.3.

### 5.6 Orchestrator → Worker → Synthesizer (only for valid RFPs)

**Orchestrator** (`orchestrator.py`): decomposes the RFP into **per-department subtasks**. Determines `departments_needed` ⊆ {`revenue`, `clinical`, `compliance`} using the department contribution table (CONTEXT §2.1). **`compliance` is always included** (§2.1). Writes `departments_needed` onto RFP metadata and creates one `DepartmentSection` per department. Handles the "no departments mentioned" case per §8.1.

**Workers** (`worker.py`, one invocation per department): each worker receives **only** shared metadata + the **department-relevant extracts** (never the whole raw doc, never PHI) — see the "needed information" contract in §8.2. Produces `key_aspects` for its department and writes them to that department’s `DepartmentSection.key_aspects` in Supabase. Records `open_questions` for anything missing (e.g. absent headcount) instead of inventing it. Workers for the three departments are independent and may run concurrently (LangGraph fan-out) — no worker depends on another’s output.

**Synthesizer** (`synthesizer.py`): consolidates all worker `key_aspects` into a single **sales-facing summary** framed as **"what to ask whom"** (for Tom Callahan / Revenue Cycle, the "Sales" reader per CONTEXT §1) — i.e. per department, the open questions and decisions Revenue needs to drive. Handles worker contradictions per §8.4. On success → `Ticket.status = intake_complete`.

### 5.7 Context-sharing model (how agents share context)

Context flows through **three separate channels**, kept deliberately narrow so PHI least-privilege (§6) and the no-consensus contradiction rule (§8.4) hold. Agents do **not** share a single global blob, and workers never talk peer-to-peer.

```
orchestrator ──scoped payload──▶ worker(revenue)    ─┐
             ──scoped payload──▶ worker(clinical)    ─┼─▶ DepartmentSection rows ──▶ synthesizer ──▶ sales summary
             ──scoped payload──▶ worker(compliance)  ─┘        (Supabase)
                                     ▲
                         workers are isolated from each other
```

1. **In-run graph state (`RfpIntakeState`, ephemeral).** The intake `StateGraph` threads one typed-dict state through every node (convert → PHI → metadata → readability → classify → orchestrate → work → synthesize). Nodes read/write it; it holds the markdown, extracted metadata, `departments_needed`, and worker results for the duration of a single ticket run only. This is the pipeline conveyor — not a place raw PHI is ever parked (content is redacted before it lands here).

2. **Scoped payloads (orchestrator → each worker, least-privilege).** A worker never receives the whole state. The orchestrator hands each worker only the §8.2 contract: `{ department_id, shared_metadata, department_extracts (redacted, this department only), open_questions }`. Consequences: no worker sees the full raw document, no worker sees PHI, and **no worker sees another worker’s output**. The three workers run as an independent fan-out and are isolated from one another — which is exactly why §8.4 can state there is no shared cell to clobber.

3. **Supabase (durable, cross-node and cross-phase).** The persistent shared record is the `DepartmentSection` rows (§7). Each worker writes `key_aspects` to **its own** department’s row. The **synthesizer** is the single recombination point: it reads all departments’ `key_aspects` back and consolidates them, surfacing cross-department contradictions as flags rather than resolving them (§8.4). Supabase is also what carries context across a re-run after a mid-way failure (§8.5) and forward into Parts 2–3.

**Net:** graph state moves the run forward, scoped payloads enforce least-privilege into each worker, and Supabase is the durable record where per-department results land and the synthesizer reads them back. Worker-to-worker context sharing is intentionally **indirect only** — upstream via the orchestrator, downstream via the synthesizer.

---

## 6. PHI handling (required in Phase 1 — CONTEXT §4.4, Part 1 deliverable)

Reuse, do not rewrite:
- `app/domains/agent/harness/input_guards.py::detect_phi` — boolean PHI presence.
- `app/domains/knowledge/pii.py::redact_pii` — produces `[REDACTED_*]` tokens.
- `app/domains/agent/memory/phi.py::validate_no_phi` — returns `(ok, reasons)` incl. named-patient/appointment heuristics.
- `data/pipelines/extract/phi.py` — as a reference for the fail-closed scanning style.

Wrap these behind `data/pipelines/rfp_intake/phi.py` so the graph calls one adapter. On detection:
1. Set the section/ticket `contains_phi=true` flag (the `DepartmentSection.evaluation_results.contains_phi: bool` slot from CONTEXT §2.3 — create the column/JSON now even though full evaluation is Part 2).
2. **Redact** the offending content before it is stored or passed to any worker/synthesizer prompt.
3. Flag for Compliance human review in the ticket (surface a banner; §5.1).
4. Never write raw PHI to `raw_pdf_path` sidecar text, logs, DB text columns, or API responses. (The PDF binary itself in `data/raw/` is the unavoidable raw artifact; everything derived from it must be scrubbed.)

Target: 100% PHI detection before content advances (CONTEXT §3). Add a dedicated unit test with the §9 PHI fixture asserting no raw patient string reaches `key_aspects`, the summary, or logs.

---

## 7. Data Model (Supabase / SQLModel — new `rfp_intake` domain)

Create SQLModel `table=True` models (mirror `reporting_models.py` style: timezone-aware `DateTime` columns, JSON columns via `sa.Column(sa.JSON)`; register in `SQLModel.metadata.create_all`). Reuse `JobRun` — do not duplicate it.

- **Ticket**: `ticket_id` (PK), `rfp_id`, `status`, `raw_pdf_path`, `created_at`, `updated_at`.
- **RfpMetadata**: `ticket_id` (FK), `client_name`, `client_country` (US/UK), `program_type`, `covered_population`, `deadline`, `budget_range`, `departments_needed` (JSON list), `readability_metrics` (JSON), `open_questions` (JSON list), `contains_phi` (bool). **No patient-identifier column, ever.**
- **DepartmentSection**: `ticket_id` (FK), `department_id` (`revenue`|`clinical`|`compliance`), `key_aspects` (JSON), and — created now, populated in later parts — `draft_content`, `evaluation_results` (JSON incl. `contains_phi: bool`), `approval_status`, `approver`, `approved_at`. Unique on (`ticket_id`, `department_id`).
- **(Optional, Phase 1) IntakeSummary** or a `sales_summary` JSON column on `Ticket`/`RfpMetadata` holding the synthesizer output.

Do **not** create the `FinalDocument` table (Part 3).

---

## 8. Required Design Decisions (answer explicitly in code + PR notes)

### 8.1 RFP does not mention departments
Default rule: **always include `compliance`** (mandatory, CONTEXT §2.1). Include `revenue` whenever any commercial/financial terms are present (essentially all institutional RFPs → treat as default-on). Include `clinical` when the RFP implies service delivery/capacity (occupational health, wellness, referral network — the three canonical program types all imply clinical). If the document genuinely names no departmental need beyond a generic request, orchestrator falls back to **{`revenue`, `clinical`, `compliance`}** (all three) and records an `open_question` noting the inference. Never emit an empty `departments_needed`.

### 8.2 Information a worker needs ("needed information" contract)
Each worker receives a typed payload:
`{ department_id, shared_metadata: {client_name, client_country, program_type, covered_population, deadline, budget_range}, department_extracts: [<redacted markdown snippets relevant to this department>], open_questions: [...] }`.
- `revenue`: financial terms, currency (USD for US / GBP for UK per `client_country`), payment/volume-driven pricing signals.
- `clinical`: program type, covered population/volume, sites/capacity implications.
- `compliance`: `client_country`, whether BAA (US/HIPAA) or DPA (UK GDPR) applies, any PHI flags.
Workers receive **department-relevant extracts only**, never the full raw doc and never PHI. Missing inputs → `open_questions`, not invented values.

### 8.3 What determines an invalid RFP
Invalid = the document is **not a prospective institutional client asking HealthCore to provide occupational-health / wellness / referral services**. Concretely discard when: it is a vendor/product pitch selling *to* HealthCore (e.g. EHR system — CONTEXT §4.3), marketing collateral, an internal memo, an unrelated form, or contains no recognizable request-for-proposal intent (no client, no requested program, no ask). Formal vs. informal format is **not** a validity criterion — an email-style request is still valid (CONTEXT §4.2). Low classifier confidence below a documented threshold → keep `analyzing`/flag for human review rather than silently discarding (document the threshold and the chosen behavior).

### 8.4 Two workers contradict on the same section
Phase 1 does **not** do free-form agent negotiation (that arbitration is Part 3, CONTEXT §7). For Phase 1: workers write to **their own department’s** `key_aspects`, so there is no shared cell to clobber. If the **synthesizer** detects a cross-department contradiction (e.g. clinical-committed capacity vs. revenue’s covered-population), it must **surface it as an explicit open item/flag in the sales summary** ("conflict: capacity vs. population — Tom to reconcile") and **must not resolve it by consensus**. PHI/compliance conflicts always defer to compliance. This keeps the contradiction visible for the Part 3 fixed-arbiter node without pre-empting it.

### 8.5 How the pipeline runs & failure mid-way
- **Trigger:** upload endpoint creates a `JobRun` (`pending`) and schedules the graph via FastAPI `BackgroundTasks`; the request returns `202` immediately.
- **Execution:** the BackgroundTask marks the `JobRun` `processing`, runs the LangGraph intake graph, updating a `checkpoint` after each node (`converted` → `phi_scanned` → `metadata` → `readability` → `classified` → `orchestrated` → `workers_done` → `synthesized`) and the `Ticket.status` at the two milestones the domain defines (`analyzing` → `discarded`|`intake_complete`).
- **Success:** `JobRun` → `completed`.
- **Failure mid-way:** wrap the run in try/except; on exception mark `JobRun` `failed` with a truncated `error_message` (mirror `pipeline.py`’s failure branch and `job_runner.mark_failed`). The `Ticket` remains `analyzing` (never left in a false-complete state); the persisted `checkpoint` records how far it got. Provide a re-run path (re-invoke the runner for that `ticket_id` from the last good checkpoint, or idempotently from scratch — upserts by (`ticket_id`,`department_id`) make re-runs safe). Reuse `job_runner.reclaim_stale_locks`/`has_processing_lock` semantics so a crashed worker’s lock is reclaimable. Provide a `__main__` CLI in `runner.py` for local re-runs (guard on `DATABASE_URL` like `pipeline.py`).

---

## 9. Seed / Test Inputs

CONTEXT §4 references `rfp-requests/healthcore/` PDFs that are **not committed to the repo**. The coding agent must:
- Treat requests 1–3 as **runtime UI uploads** for manual/e2e verification; if the PDFs are unavailable, create minimal stand-in PDFs that match the described content (Meridian Manufacturing formal RFP → accept; Thames Valley University informal email RFP → accept; EHR vendor pitch → discard). Do not commit any PHI.
- **Create the PHI critical-case PDF** (CONTEXT §4.4): an "RFP" attaching a clinical case summary with a fabricated patient name + diagnosis, used **only** as a test asset to prove detect/redact/flag — and ensure that content never lands in DB columns, logs, `key_aspects`, or the summary. Keep it under `tests/` fixtures, clearly marked synthetic, and confirm `.gitignore`/scrubbing keeps raw PHI out of tracked artifacts.

---

## 10. Unit Tests — `tests/pipelines/`

Follow `tests/pipelines/test_pipeline.py` conventions (repo-root pytest, `pythonpath = ["services/api", "."]`). Cover at minimum:

1. **Convert:** markitdown produces non-empty markdown from a sample PDF (mock/tiny fixture).
2. **Readability:** metrics computed and shaped correctly; tokenizer-unavailable path degrades gracefully (§5.4).
3. **Metadata extraction:** given a canned LLM response (mock the proxy via `respx`, as existing tests do), fields map correctly; missing fields become `open_questions` and are never fabricated.
4. **Classifier:** formal RFP → valid; informal email RFP → valid; EHR vendor pitch → invalid → ticket `discarded`; low-confidence handling.
5. **Orchestrator:** `compliance` always present; "no departments mentioned" → all-three fallback with an open question (§8.1); never empty.
6. **Worker:** receives only shared metadata + department extracts (assert no full-doc/PHI leakage); missing headcount → `open_question`, not invented.
7. **Synthesizer:** consolidates key_aspects into a "what to ask whom" summary; cross-department contradiction surfaced as a flag, not resolved (§8.4).
8. **PHI (critical):** §9 PHI fixture → `contains_phi=true`, content redacted, and **no raw patient string** appears in `key_aspects`, summary, ticket response, or captured logs.
9. **Status machine:** happy path `analyzing → intake_complete`; invalid → `discarded`; simulated mid-way exception → `JobRun=failed`, ticket stays `analyzing`, checkpoint recorded (§8.5).

Mock all LLM calls (`respx` against `llm.4geeks.ai`) and run DB assertions against a test engine / transactional session per existing patterns. No live network, no real PHI.

---

## 11. Dependencies to add

- `markitdown` (PDF → markdown).
- `py-readability-metrics` (import name `readability`) + deterministic NLTK `punkt` availability (§5.4).
- Add to `services/api/pyproject.toml`, run `uv lock`, verify the workspace still resolves. No new LLM SDKs — use the existing httpx proxy convention.

---

## 12. Development Workflow

1. `git checkout feature/agent_memory && git pull` → `git checkout -b feature/rfp-intake`.
2. Follow `AGENTS.md`: read `memory-bank/{projectbrief,techContext,progress,conventions,decisions}.md` and applicable `.agents/rules/*` (frontend rules for `uis/` work) before building.
3. Implement in dependency order: models/migrations → upload endpoint + Ticket + `data/raw` storage + JobRun enqueue → pipeline convert/PHI/metadata/readability/persist → classifier → orchestrator/worker/synthesizer → backoffice UI → tests.
4. Keep the CX agent graph (`app/domains/agent/graph.py`) untouched; the intake graph is separate under `data/pipelines/rfp_intake/`.
5. Run `uv run pytest tests/pipelines -q` (plus touched frontend lint/build) before proposing a commit. Per `AGENTS.md` §3, update `memory-bank/progress.md` + `decisions.md` and **request developer acknowledgement before committing**.
6. PR description must include: the §3 availability check, the five §8 design decisions, PHI-handling summary, and what was validated vs. residual gaps.

---

## 13. Acceptance Criteria (Phase 1 "done")

- [ ] Authenticated PDF upload in `uis/backoffice/rfp-intake` creates a `Ticket` (`analyzing`), stores the PDF under `data/raw/` with a non-PHI filename, and returns `202` without blocking.
- [ ] `rfp_intake` pipeline converts PDF→markdown (markitdown), scans/redacts PHI, extracts metadata (no invented values), computes readability metrics, and persists metadata+metrics to Supabase on the ticket.
- [ ] Classifier discards non-RFPs (EHR pitch → `discarded`) and accepts formal + informal RFPs.
- [ ] For valid RFPs, orchestrator produces `departments_needed` (always incl. `compliance`), workers write per-department `key_aspects` (metadata + department extracts only, no PHI), synthesizer produces a "what to ask whom" sales summary, and the ticket reaches `intake_complete`.
- [ ] PHI critical case is detected, redacted, flagged for compliance, and never surfaced in DB/logs/UI/summary.
- [ ] Mid-way failure marks `JobRun=failed`, leaves the ticket non-`intake_complete`, and is re-runnable.
- [ ] `tests/pipelines/` covers §10; `uv run pytest tests/pipelines` passes.
- [ ] `markitdown` + `py-readability-metrics` added and locked; no PHI committed.

---

## 14. Open Clarifying Questions (resolved + still-open)

**Resolved with the requester:**
- Spec location → `multi_agent_assignments/` (this file). ✔
- Pipeline run model → FastAPI `BackgroundTasks` + `JobRun`. ✔
- Status naming → underscore (`intake_complete`) per CONTEXT §2.3. ✔
- PHI detect/block/redact → **required in Phase 1**. ✔

**Recommend confirming before/while building (won’t block a first pass; defaults noted):**
1. **Markdown storage:** sidecar file under `data/raw/` vs. a DB text column? *Default: DB text column (scrubbed) so nothing PHI-adjacent lives loose on disk; the PDF binary stays the only raw artifact.*
2. **Auth scope:** is the existing HealthCore JWT (`get_current_user`) sufficient, or must uploads be restricted to Revenue Cycle role specifically? *Default: reuse `get_current_user` like other backoffice routers; add role gating if the auth domain already models roles.*
3. **Backoffice hosting:** does `uis/backoffice/` use a shared Next.js shell that mounts per-feature `components/hooks/lib` (like `knowledge/`), or does each feature ship its own app? Confirm where the `rfp-intake` route mounts.
4. **`covered_population` type:** free text vs. structured integer + unit (employees/students)? *Default: store the verbatim string + a nullable parsed integer; never coerce/invent.*
5. **Classifier confidence threshold** for the "uncertain → human review vs. discard" branch (§8.3) — pick a number (suggest 0.5) and confirm the desired behavior below it.

---

## 15. Suggested Additional Tasks (improve model outcomes / robustness)

1. **Few-shot the classifier & metadata extractor** with the three CONTEXT §4 archetypes (formal RFP, informal email RFP, vendor pitch) as in-context examples — materially improves precision on informal RFPs and vendor-pitch rejection.
2. **Structured outputs via JSON schema / function-calling** (if the proxy supports it) instead of free-text JSON parsing, to cut malformed-JSON retries; keep the fenced-JSON fallback.
3. **Add lightweight evals** (extend the `data/eval/` pattern) tracking CONTEXT §3 KPIs: correct-classification rate and PHI-detection rate, so regressions are visible.
4. **Confidence + provenance on extracted metadata:** store per-field confidence and the source snippet offset; feeds the "open questions" logic and later human review.
5. **Idempotency key on upload** (hash of file bytes) to avoid duplicate tickets on double-submit.
6. **A `data/pipelines/rfp_intake/README.md`** documenting the graph, checkpoints, and re-run procedure (matches the existing pipeline READMEs).
7. **Observability:** emit the same trace-step pattern the CX agent uses (`trace_steps`) so intake runs are inspectable; never log raw document text.
8. **Golden markdown fixtures** committed for the three archetypes (post-markitdown, PHI-free) so classifier/metadata tests don’t depend on PDF parsing.

---

## 16. Suggested Models (fit for this use case)

The backend talks to an **OpenAI-compatible proxy at `llm.4geeks.ai`** (`settings.generation_model`, currently `deepseek/deepseek-v4-flash` via OpenRouter). Recommendations, in priority order:

1. **Keep `settings.generation_model` (deepseek-v4-flash) as the default** for classifier/orchestrator/worker/synthesizer — cheap, fast, temperature 0, adequate for structured extraction and short reasoning. No code change; consistent with the rest of the app.
2. **For the metadata extractor + classifier specifically**, prefer a model with strong instruction-following and reliable JSON. If the proxy exposes it, a mid-tier **Claude** model (e.g. a Sonnet-class model — latest is **Claude Sonnet 5**, id `claude-sonnet-5`) is a strong fit for structured, high-recall extraction and for the **PHI-sensitivity judgment**, where instruction adherence matters most. Anthropic’s latest families are Claude 5 (`claude-opus-5`, `claude-sonnet-5`, `claude-fable-5`) and Haiku 4.5 (`claude-haiku-4-5-20251001`).
3. **For the synthesizer** (consolidation + "what to ask whom" framing + contradiction surfacing), a slightly stronger reasoning model improves the summary quality — a Sonnet-class model is the sweet spot; reserve an Opus-class model only if summaries prove weak.
4. **Make the model configurable per node** (add e.g. `rfp_classifier_model`, `rfp_synthesizer_model` settings defaulting to `generation_model`) so quality/cost can be tuned without code changes and Phase 1 stays single-model by default.
5. **Do not** switch SDKs to reach these models — route everything through the existing proxy convention; only the `model` string changes.

> Note: model choice does not relax any §4 constraint — PHI blocking is enforced by the deterministic detectors in §6, not by the LLM.
