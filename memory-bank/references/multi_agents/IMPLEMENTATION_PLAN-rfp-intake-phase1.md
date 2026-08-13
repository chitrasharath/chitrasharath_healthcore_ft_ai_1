# RFP Intake Phase 1 — Implementation Plan

**Plan file:** [`IMPLEMENTATION_PLAN-rfp-intake-phase1.md`](IMPLEMENTATION_PLAN-rfp-intake-phase1.md)

**Requirements source (authoritative):**
- [`SPEC-rfp-intake-phase1.md`](SPEC-rfp-intake-phase1.md) — Part 1 only
- [`CONTEXT-multi_agent.md`](CONTEXT-multi_agent.md) — domain rules for Parts 1–3

**Prerequisite:** Agent Memory delivered on `feature/agent_memory` (PHI helpers, LangGraph patterns, JobRun, Supabase SQLModel, backoffice Knowledge app template).

**Branch:** `feature/rfp-intake` off `origin/feature/agent_memory`. PR → `feature/agent_memory`.

**Working directories:**

| Area | Path |
|------|------|
| API domain (new) | `services/api/app/domains/rfp_intake/` |
| Router wiring | `services/api/app/api/v1/router.py` |
| JobRun extension | `app/domains/jobs/models.py`, `job_runner.py` |
| Intake pipeline / graph (new) | `data/pipelines/rfp_intake/` |
| Uploaded PDFs (runtime) | `data/raw/{ticket_id}.pdf` |
| Frontend feature module (new) | `uis/backoffice/rfp-intake/` |
| Landing mount | `uis/backoffice/landing/` — route, alias, nav card, Tailwind `@source` |
| Dependencies | `services/api/pyproject.toml` + both `uv.lock` files |
| Tests | `tests/pipelines/test_rfp_intake*.py`, `services/api/tests/test_rfp_intake.py`, landing Jest as needed |
| Fixtures | `tests/fixtures/rfp_intake/` (golden markdown; optional tiny PDFs; PHI synthetic in-memory / gitignored) |
| Docs | `data/pipelines/rfp_intake/README.md`; PR notes per SPEC §3 / §8 / §12 |

**Status:** Plan ready — implement only after developer go-ahead.

**Rule:** Spec + locked planning clarifications below override any ambiguity. Do **not** mix into the CX agent graph (`app/domains/agent/graph.py`). Do **not** invent headcount/budget/PHI. Do **not** commit until the developer explicitly asks. Parts 2–3 are out of scope but must not be architecturally precluded (same `Ticket` + `DepartmentSection` rows).

---

## Executive summary

Deliver **Milestone 9 Part 1 (RFP intake)** only:

1. Authenticated backoffice PDF upload → `Ticket` (`analyzing`) + PDF under `data/raw/` + `JobRun` → `202`.
2. Dedicated LangGraph under `data/pipelines/rfp_intake/`: convert → PHI redact → metadata → readability → classify → orchestrate → workers → synthesize.
3. Persist `RfpMetadata` + per-department `DepartmentSection.key_aspects` + sales summary in **Supabase**.
4. Ticket ends `intake_complete` or `discarded` (or stays `analyzing` on failure / low-confidence human review).
5. UI at `/rfp-intake` (knowledge-style module) with list/detail, polling, PHI compliance banner (redacted only).

```mermaid
flowchart TD
  ui["uis/backoffice/rfp-intake upload"] --> post["POST /api/v1/rfp-intake/uploads"]
  post --> ticket["Ticket analyzing + PDF data/raw"]
  ticket --> job["JobRun pending → BackgroundTasks"]
  job --> graph["data/pipelines/rfp_intake LangGraph"]
  graph --> conv["convert markitdown"]
  conv --> phi["PHI scan/redact"]
  phi --> meta["extract metadata"]
  meta --> read["readability metrics"]
  read --> cls["classifier-agent"]
  cls -->|invalid| disc["status discarded STOP"]
  cls -->|low confidence| hold["status analyzing + human_review"]
  cls -->|valid| orch["orchestrator"]
  orch --> w["workers fan-out revenue/clinical/compliance"]
  w --> syn["synthesizer sales summary"]
  syn --> done["status intake_complete"]
```

---

## Locked decisions (spec + planning Q&A)

| # | Topic | Decision |
|---|--------|----------|
| 1 | Branch / PR | `feature/rfp-intake` ← `origin/feature/agent_memory`; PR → `feature/agent_memory` |
| 2 | §15 extras **in** | Few-shot classifier/metadata examples; golden markdown fixtures; `rfp_intake/README.md`; upload idempotency (SHA-256 of file bytes); readability tokenizer graceful degrade |
| 2b | §15 extras **defer** | Per-node model settings; full `data/eval/` KPI suite; JSON-schema/function-calling; full CX `trace_steps` parity (checkpoint string on JobRun is enough) |
| 3 | Markdown storage | **Scrubbed text column** on `RfpMetadata` (`markdown_text`); PDF binary is the only raw on-disk artifact |
| 4 | Auth | Existing HealthCore JWT via `Depends(get_current_user)` — **no** Revenue Cycle role gate |
| 5 | `covered_population` | `covered_population: str \| null` (verbatim) + `covered_population_n: int \| null` (parse only when clear); else `open_questions` — never invent |
| 6 | Classifier confidence | Threshold **0.5**. Below → keep `analyzing`, set `needs_human_review=true` + reason; **do not** discard |
| 7 | PHI mid-intake | **Continue** on redacted text through classify → workers → synthesizer → `intake_complete`, with `contains_phi=true` + UI compliance banner. Hard-stop is Part 3 `phi-detected` arbiter |
| 8 | Department extracts | **Keyword/section heuristics first**; short LLM refine only if snippets are thin. Workers never get full doc or PHI |
| 9 | Mid-way re-run | **From-scratch idempotent upsert** by `ticket_id` / (`ticket_id`,`department_id`). Checkpoint records progress for diagnosis only |
| 10 | Sales summary | **`sales_summary` JSON column on `RfpMetadata`** — no `IntakeSummary` / `FinalDocument` table |
| 11 | UI mount | Landing `/rfp-intake` + hub nav card; module `uis/backoffice/rfp-intake/` aliased like `knowledge` |
| 12 | Test fixtures | Commit PHI-free **golden markdown** for 3 archetypes; minimal PDF only if convert tests need it (else mock markitdown); PHI critical case as **synthetic in-memory / gitignored** test asset — never commit raw patient strings |
| 13 | Plan path | This file under `memory-bank/references/multi_agents/` |
| 14 | Models | Single `settings.generation_model` (deepseek-v4-flash) for all LLM nodes; httpx proxy only — no new LLM SDKs |
| 15 | JobRun reuse | Extend `JobRun` with nullable `target_key` (ticket_id) + `checkpoint`; `job_name="rfp_intake"`; keep `target_date` = UTC date of enqueue for existing index |
| 16 | Status vocabulary | Underscores only: `analyzing`, `discarded`, `intake_complete` |
| 17 | Git commits | **No commits until the developer explicitly asks** |

---

## Prerequisites

- [ ] On / based off `origin/feature/agent_memory`
- [ ] Spec + CONTEXT + this plan read end-to-end before coding
- [ ] `DATABASE_URL` / Supabase available for local smoke (pytest uses in-memory/test engine pattern)
- [ ] `LLM_API_KEY` optional for live smoke; tests mock via `respx`
- [ ] Load applicable `.agents/rules/frontend/*` before UI work
- [ ] Re-read `.agents/rules/frontend/README.md` and utilities README for touched paths

---

## Phase 0 — Branch, dependencies, availability check

### 0.1 Branch

```bash
git fetch origin
git checkout -b feature/rfp-intake origin/feature/agent_memory
```

### 0.2 Dependencies

Add to `services/api/pyproject.toml` (then `uv lock` in **both** `services/api` and repo root):

- `markitdown` (PDF → markdown)
- `py-readability-metrics` (import name `readability`)

NLTK `punkt`: prefer **graceful degrade** when tokenizer data is missing (`readability_metrics: { "status": "unavailable", "reason": "..." }`) so the job never fails solely on metrics. Optionally document a one-time `nltk.download("punkt")` for local/Docker if metrics are desired in smoke runs. Do **not** fail closed on readability.

### 0.3 Availability check (PR description checklist)

Confirm and note in PR:

1. `markitdown` + `py-readability-metrics` added and locked  
2. `data/pipelines/rfp_intake/` created  
3. Seed PDFs from CONTEXT §4 are **not** assumed committed — UI/runtime or stand-in fixtures  
4. Multipart upload endpoint is net-new  
5. PHI critical-case fixture created for tests (synthetic; no committed PHI)

---

## Phase 1 — Data model + JobRun extension

### 1.1 SQLModel tables (`app/domains/rfp_intake/models.py`)

Register via existing `SQLModel.metadata.create_all(supabase_engine)` on API startup (same pattern as inventory/telemetry). No separate migration framework.

**Ticket**

| Column | Notes |
|--------|--------|
| `ticket_id` | PK, UUID string |
| `rfp_id` | Generated business id (e.g. `RFP-{short}`) |
| `status` | `analyzing` \| `discarded` \| `intake_complete` |
| `raw_pdf_path` | e.g. `data/raw/{ticket_id}.pdf` |
| `content_sha256` | Upload idempotency |
| `needs_human_review` | bool, default false |
| `classifier_reason` | nullable text |
| `created_at` / `updated_at` | timezone-aware DateTime |

**RfpMetadata** (1:1 with ticket)

| Column | Notes |
|--------|--------|
| `ticket_id` | PK/FK |
| `client_name`, `client_country` (US/UK), `program_type` | nullable until extracted |
| `covered_population` | verbatim string \| null |
| `covered_population_n` | int \| null |
| `deadline`, `budget_range` | nullable |
| `departments_needed` | JSON list |
| `readability_metrics` | JSON |
| `open_questions` | JSON list |
| `contains_phi` | bool |
| `markdown_text` | scrubbed markdown (DB text) |
| `sales_summary` | JSON (synthesizer output) |
| `classifier_result` | JSON `{is_rfp, confidence, reason}` optional |

**DepartmentSection**

| Column | Notes |
|--------|--------|
| `id` | PK |
| `ticket_id` + `department_id` | unique together; `revenue` \| `clinical` \| `compliance` |
| `key_aspects` | JSON |
| `draft_content` | nullable — Part 2 |
| `evaluation_results` | JSON incl. `contains_phi: bool` — create now |
| `approval_status`, `approver`, `approved_at` | Part 3 placeholders |

Do **not** create `FinalDocument`.

### 1.2 JobRun extension

Extend `JobRun` (backward-compatible):

- `target_key: str | None` — store `ticket_id` for `rfp_intake`
- `checkpoint: str | None` — `converted` → `phi_scanned` → `metadata` → `readability` → `classified` → `orchestrated` → `workers_done` → `synthesized`

Add helpers in `job_runner.py`:

- `create_pending_for_key(session, job_name, target_key, target_date)`  
- `set_checkpoint(session, run, checkpoint)`  
- Keep existing date-based APIs for nightly export unchanged  
- Reuse `reclaim_stale_locks` / `has_processing_lock` with `job_name="rfp_intake"` (lock granularity: one processing job per name is existing semantics — document that concurrent RFP uploads may serialize on reclaim checks, **or** narrow lock check to `target_key` if concurrent uploads are required; prefer **per-`target_key` processing lock** for this feature)

### 1.3 Schemas + repository

- Pydantic request/response schemas (upload 202 body; ticket list/detail — **redacted only**).
- `repository.py` in pipeline package for upserts (API service may call shared store helpers to avoid duplicating SQL).

---

## Phase 2 — Upload API + background enqueue

### 2.1 Domain package

```
services/api/app/domains/rfp_intake/
  __init__.py
  models.py
  schemas.py
  service.py
  router.py
  store.py          # optional if not importing pipeline repository
```

Wire router in `app/api/v1/router.py` behind `Depends(get_current_user)` (match knowledge/agent).

### 2.2 Endpoints

| Method | Path | Behavior |
|--------|------|----------|
| `POST` | `/api/v1/rfp-intake/uploads` | Multipart PDF only; max ~20 MB; idempotent on `content_sha256` (return existing ticket if completed/in-flight); create Ticket + write `data/raw/{ticket_id}.pdf`; `JobRun` pending; `BackgroundTasks` → runner; **202** `{ ticket_id, rfp_id, status }` |
| `GET` | `/api/v1/rfp-intake/tickets` | List summary rows |
| `GET` | `/api/v1/rfp-intake/tickets/{ticket_id}` | Ticket + metadata + sections + summary; never raw PHI |
| `POST` | `/api/v1/rfp-intake/tickets/{ticket_id}/rerun` | From-scratch re-run (idempotent upserts); reclaim stale lock first |

Reject non-PDF with `400`/`415`. Never block request on pipeline completion.

### 2.3 Background task contract

1. Mark JobRun `processing`  
2. Invoke `data.pipelines.rfp_intake.runner.run_intake(ticket_id)`  
3. On success → JobRun `completed`  
4. On exception → JobRun `failed` + truncated `error_message`; Ticket stays `analyzing` (unless already `discarded`/`intake_complete`)

---

## Phase 3 — `data/pipelines/rfp_intake` graph

### 3.1 Package layout

```
data/pipelines/rfp_intake/
  __init__.py
  README.md
  state.py              # RfpIntakeState TypedDict
  graph.py              # StateGraph compile
  runner.py             # BackgroundTask entry + __main__ CLI
  convert.py
  phi.py                # adapter over existing detectors
  metadata.py
  readability.py
  repository.py
  extracts.py           # heuristic department snippets (+ optional LLM refine)
  agents/
    classifier.py
    orchestrator.py
    worker.py
    synthesizer.py
  prompts/              # few-shot examples for classifier + metadata
```

Reuse `pipeline.py` conventions: sys.path bootstrap, `_ensure_engine`, try/except → failed run. **Do not modify** `data/pipelines/pipeline.py` telemetry flow beyond shared patterns.

### 3.2 Node order + checkpoints

| Step | Node | Checkpoint | Persist |
|------|------|------------|---------|
| 1 | convert | `converted` | scrubbed markdown → `RfpMetadata.markdown_text` after PHI step |
| 2 | phi | `phi_scanned` | redact; set `contains_phi`; seed `evaluation_results.contains_phi` when sections exist |
| 3 | metadata | `metadata` | structured fields + `open_questions`; never invent |
| 4 | readability | `readability` | metrics JSON or `{status: unavailable}` |
| 5 | classify | `classified` | discard / human_review / continue |
| 6 | orchestrate | `orchestrated` | `departments_needed` + `DepartmentSection` rows |
| 7 | workers | `workers_done` | per-dept `key_aspects` |
| 8 | synthesize | `synthesized` | `sales_summary`; status `intake_complete` |

### 3.3 PHI adapter (`phi.py`)

Reuse only:

- `detect_phi` (harness input_guards)
- `redact_pii` (knowledge)
- `validate_no_phi` (agent memory)
- Style reference: `data/pipelines/extract/phi.py`

On detection: flag + redact before any downstream prompt, DB text, log, or API field. PDF binary remains under `data/raw/` as unavoidable raw artifact.

### 3.4 Classifier

- Structured `{ is_rfp, confidence, reason }` via fenced-JSON parse (existing agent pattern).
- Few-shot: formal RFP, informal email RFP, EHR vendor pitch.
- Accept formal **and** informal; discard vendor/non-RFP.
- `confidence < 0.5` → `needs_human_review=true`, stop without discard/orchestrate.
- Invalid → `status=discarded`, stop.

### 3.5 Orchestrator → workers → synthesizer

**Orchestrator (§8.1):** always include `compliance`; default-on `revenue` + `clinical` for canonical program types; if unclear → all three + open question. Never empty `departments_needed`.

**Extracts (§8.2 / locked #8):** `extracts.py` builds per-department redacted snippets via keywords (finance/currency/BAA/DPA/capacity/clinic/HIPAA/GDPR/etc.). Optional LLM refine only when empty/thin.

**Workers:** typed payload only; independent LangGraph fan-out; write own `key_aspects`; missing volume → `open_questions`.

**Synthesizer:** "what to ask whom" for Tom Callahan; surface cross-dept contradictions as flags (**no consensus resolution**); PHI/compliance conflicts defer to compliance framing.

### 3.6 Context-sharing model (enforce in code)

1. Ephemeral `RfpIntakeState` (redacted content only)  
2. Scoped orchestrator → worker payloads (no peer worker visibility)  
3. Supabase `DepartmentSection` as durable recombination input for synthesizer  

### 3.7 CLI re-run

`python -m data.pipelines.rfp_intake.runner --ticket-id …` (or `uv run`) guarded on `DATABASE_URL` like telemetry pipeline.

---

## Phase 4 — Backoffice UI

### 4.1 Module + landing wiring

Mirror `uis/backoffice/knowledge/`:

```
uis/backoffice/rfp-intake/
  components/
  hooks/
  lib/rfp-intake-api.ts
  types/
```

Landing:

- `next.config.ts` + `tsconfig` alias `@backoffice/rfp-intake`
- `app/(protected)/rfp-intake/page.tsx` (+ detail route if split)
- `lib/nav-apps.ts` nav card
- Tailwind `@source` for the new folder
- Jest alias if API helpers are unit-tested

### 4.2 UX requirements

- PDF upload: `application/pdf` only; client max size ~20 MB  
- On 202: show `ticket_id` + `analyzing`  
- List/detail: status, client, program, departments, readability summary  
- When `intake_complete`: per-dept `key_aspects` + sales summary  
- When `discarded`: classifier reason  
- When `contains_phi`: compliance banner; **redacted preview only**  
- When `needs_human_review`: banner + reason; no auto-discard  
- Poll or manual refresh for status transitions  

Components ≤80 lines; follow frontend agent rules.

---

## Phase 5 — Tests

Follow `tests/pipelines/test_pipeline.py` conventions; mock LLM with `respx` against proxy URL; no live network; no real PHI in git.

Minimum coverage (SPEC §10):

1. Convert — non-empty markdown (fixture PDF or mocked markitdown)  
2. Readability — shape OK; unavailable path does not fail job  
3. Metadata — fields map; missing → `open_questions`; no fabrication  
4. Classifier — formal valid; informal valid; EHR → `discarded`; low confidence → human review  
5. Orchestrator — `compliance` always; all-three fallback; never empty  
6. Worker — no full-doc/PHI leakage; missing headcount → open question  
7. Synthesizer — summary + contradiction flag, not resolved  
8. PHI critical — `contains_phi=true`, redacted, **no raw patient string** in key_aspects/summary/API/logs  
9. Status machine — happy path; discard; mid-way failure → JobRun failed, ticket `analyzing`, checkpoint set  
10. Upload idempotency — same SHA returns existing ticket  

Also: `services/api/tests/test_rfp_intake.py` for auth + multipart + 202 + GET redaction.

Verification before proposing commit:

```bash
uv run pytest tests/pipelines/test_rfp_intake*.py services/api/tests/test_rfp_intake.py -q
cd uis/backoffice/landing && npm run verify
```

---

## Phase 6 — Docs, memory-bank, handoff

1. `data/pipelines/rfp_intake/README.md` — graph, checkpoints, re-run, PHI rules, readability note  
2. Update `memory-bank/progress.md` and `memory-bank/decisions.md` when implementation completes (before commit request)  
3. PR description must include: §3 availability check, five §8 design decisions (as implemented), PHI summary, validated vs residual gaps  
4. Manual smoke (optional): upload stand-in Meridian / Thames / EHR PDFs through UI when available  

---

## Implementation order (dependency)

1. Phase 0 — branch + deps  
2. Phase 1 — models + JobRun extension  
3. Phase 2 — upload/list/detail/rerun API + BackgroundTasks stub calling runner  
4. Phase 3 — pipeline nodes incrementally (convert→PHI→metadata→readability→classify→orch/work/syn) with tests per node  
5. Phase 4 — UI  
6. Phase 5 — full suite green  
7. Phase 6 — README + memory-bank + PR notes  

---

## Out of scope (Parts 2–3 / deferred)

- Section draft generation + evaluator loops  
- Human approval HITL + fixed arbitration node (`phi-detected`, `baa-dpa-mismatch`, `capacity-vs-population`)  
- `FinalDocument` table  
- Revenue Cycle RBAC  
- Per-node LLM model settings / full eval harness / function-calling structured outputs  
- Changes to CX agent graph or MCP company-tools  

---

## Acceptance criteria (Phase 1 done)

- [ ] Authenticated PDF upload creates Ticket `analyzing`, stores non-PHI filename under `data/raw/`, returns 202 without blocking  
- [ ] Pipeline converts, PHI-scans/redacts, extracts metadata (no invented values), readability (or unavailable), persists to Supabase  
- [ ] Classifier: EHR → `discarded`; formal + informal → continue; low confidence → human review  
- [ ] Orchestrator always includes `compliance`; workers write scoped `key_aspects`; synthesizer "what to ask whom"; ticket → `intake_complete`  
- [ ] PHI critical case flagged/redacted/never in DB text/logs/UI/summary raw form  
- [ ] Mid-way failure → JobRun `failed`, ticket not falsely complete, re-runnable from scratch  
- [ ] `tests/pipelines` §10 coverage green; deps locked; no PHI committed  
- [ ] `/rfp-intake` UI list/detail/upload/poll works behind AuthGuard  

---

## Residual risks

| Risk | Mitigation |
|------|------------|
| `JobRun` originally date-keyed | Nullable `target_key` + per-key lock; leave nightly jobs untouched |
| BackgroundTasks lost on process restart | Ticket stays `analyzing`; CLI/API re-run; stale lock reclaim |
| markitdown quality on informal email PDFs | Golden markdown fixtures + few-shot classifier; accept informal intent |
| NLTK punkt offline | Graceful `readability` unavailable path |
| Heuristic extracts miss content | Thin-snippet LLM refine; open_questions when empty |
| Concurrent uploads | Per-`target_key` processing lock |

---

## Change / risk summary template (pre-commit)

When asking for commit acknowledgement, fill:

- **Changed:** …  
- **Validated:** …  
- **Residual risks:** …  
