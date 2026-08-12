# SPEC — RFP Intake, Phase 2 (Milestone 9, Part 2): Generator ↔ Evaluator Loop

> **Audience:** the coding agent implementing this feature.
> **Source of truth for domain rules:** [`CONTEXT-multi_agent.md`](./CONTEXT-multi_agent.md) — read it in full. This spec operationalizes **Part 2 only**.
> **Prior work:** [`SPEC-rfp-intake-phase1.md`](./SPEC-rfp-intake-phase1.md) — Phase 2 **extends** Phase 1; reuse its models, statuses, module layout, LLM convention, and PHI detectors. Do not re-implement them.
> **Repo:** `chitrasharath_healthcore_ft_ai_1/` (the HealthCore monorepo).
> **Base branch:** `feature/rfp-intake` (Phase 1 implemented) → **new work branch:** `feature/rfp-response-generation`.

---

## 1. Project Overview

Phase 1 turned an uploaded PDF into a validated `Ticket` with per-department `key_aspects` (revenue, clinical, compliance) and a sales-facing summary, ending at status `intake_complete`. **Phase 2 turns those key_aspects into evaluated draft sections.**

For each department, a **generator agent** writes that department's proposal section from its `key_aspects` + shared metadata. Three **evaluator agents run in parallel** — readability, relevance, compliance — and produce a single `EvaluationResult`. On failure, the section returns to its generator with **concrete, actionable feedback**, the generator revises, and it is re-evaluated. This generator↔evaluator loop runs under an **iteration limit**; when the limit is hit, the last draft + EvaluationResult are kept and the section is flagged `needs_human_review` for sales. PHI in any draft is a **hard stop** (no looping).

Phase 2 is the **generation + evaluation** stage. Per-department human approval, conflict arbitration, and final-document generation are **Part 3 — out of scope here** but must not be precluded (the same `Ticket` and `DepartmentSection` rows carry forward; the `approval_*` columns already exist unused).

### 1.1 End-to-end flow (Phase 2, per department, independent loops)

```
Ticket intake_complete ──[sales clicks "Start drafting" in backoffice]──▶ Ticket status = drafting
        │  POST /tickets/{id}/start-drafting → new JobRun job_name="rfp_drafting", FastAPI BackgroundTask
        ▼
  For each DepartmentSection (revenue, clinical, compliance) — INDEPENDENT loop:

        ┌───────────────────────────────────────────────────────────┐
        │  section.status = drafting                                 │
        │  [generator(dept)] key_aspects + metadata (+ feedback) ─▶ draft_content
        │                                                            │
        │  section.status = under_evaluation                         │
        │        ├─▶ [readability evaluator] ─┐                      │
        │        ├─▶ [relevance evaluator]   ─┼─▶ [aggregate] ─▶ EvaluationResult
        │        └─▶ [compliance evaluator]  ─┘   (single writer)    │
        │                                                            │
        │  overall_pass? ── yes ─▶ section.status = passed  (exit)   │
        │       │                                                    │
        │       no ──▶ iterations < limit? ── yes ─▶ loop w/ feedback│
        │                     │                                      │
        │                     no ─▶ keep draft + result,             │
        │                           section.status = needs_human_review (exit)
        │  PHI detected at any point ─▶ HARD STOP: needs_human_review,│
        │                               flag Compliance (no loop)    │
        └───────────────────────────────────────────────────────────┘

  When every section ∈ {passed, needs_human_review}: Phase 2 done.
  Ticket rollup: under_evaluation while any loop active; flags "N section(s) need human review".
```

---

## 2. Tech Stack (reuse Phase 1 — no parallel stacks)

Identical to Phase 1 (see that spec §2). Salient reuse for Phase 2:

| Concern | Reuse |
| --- | --- |
| Multi-agent graph | **LangGraph** `StateGraph` under `data/pipelines/rfp_intake/` (extend, do **not** touch `app/domains/agent/graph.py`) |
| Parallel evaluators | LangGraph fan-out + a join/aggregate node (see §8.2 for the concurrency rule) |
| LLM calls | OpenAI-compatible proxy `llm.4geeks.ai`, `settings.generation_model`, httpx, temperature 0, fenced-JSON parse — **no new SDKs** |
| Readability | the Phase 1 `data/pipelines/rfp_intake/readability.py` wrapper over `py-readability-metrics` (already added + `punkt` handled) |
| PHI detection | the Phase 1 `data/pipelines/rfp_intake/phi.py` adapter over `detect_phi` / `redact_pii` / `validate_no_phi` |
| DB (source of truth) | Supabase via SQLModel; `Ticket` / `DepartmentSection` already exist |
| Run/job model | new `JobRun` (`job_name="rfp_drafting"`) + FastAPI `BackgroundTasks`, same as Phase 1 §8.5 |
| Backoffice | extend `uis/backoffice/rfp-intake/` (Next.js App Router) shipped in Phase 1 |

---

## 3. Availability Verification (confirm before building)

Phase 2 assumes Phase 1 landed on `feature/rfp-intake`. Verify these exist; if any are missing, that is a Phase 1 gap to reconcile first:

| Need | Expected from Phase 1 | If missing |
| --- | --- | --- |
| `DepartmentSection` with `draft_content`, `evaluation_results` (JSON), `approval_*` columns | SPEC1 §7 | add the columns |
| Per-department `key_aspects` populated + ticket at `intake_complete` | SPEC1 §5.6 | Phase 1 not complete — stop |
| `readability.py` wrapper (metrics + graceful `punkt` fallback) | SPEC1 §5.3/§5.4 | add per SPEC1 |
| `phi.py` adapter over the shared detectors | SPEC1 §6 | add per SPEC1 |
| `JobRun` state machine + `job_runner.py` | base repo | present on base |
| Backoffice `rfp-intake` app + ticket detail view | SPEC1 §5.1 | add per SPEC1 |
| LangGraph intake graph + `runner.py` entrypoint pattern | SPEC1 §5.3 | add per SPEC1 |

**New for Phase 2 (build these):** generator agents, the three evaluator agents, the aggregate node, the loop controller, the `EvaluationResult` persistence, Phase-2 status transitions, the **"Start drafting" trigger endpoint + button**, and the backoffice draft/evaluation panels. **No new Python packages are required** (readability + PHI utils already added in Phase 1).

---

## 4. Constraints (non-negotiable — inherit all of Phase 1 §4, plus)

1. **PHI is a hard stop, everywhere.** No patient identifier/PHI in any draft, evaluation record, log, DB text column, or UI — not even illustrative (CONTEXT §0, §5). A draft containing PHI is **never** looped back for another attempt; it goes straight to `needs_human_review` + Compliance flag (§8 / decision).
2. **Compliance is mandatory on every RFP** and the compliance evaluator is always one of the three evaluators, for every department's section (CONTEXT §2.1, §5). Its no-PHI check is a **mandatory** evaluation criterion (CONTEXT Part 2 deliverable).
3. **Country-correct regulatory instrument** (CONTEXT §5): US client sections must carry a **BAA** clause; UK client sections a **DPA / UK GDPR** clause. Pricing currency is **USD for US, GBP for UK**, keyed off `client_country`. The compliance evaluator enforces these as rules.
4. **Never invent data** (CONTEXT §2.3): generators must not fabricate headcount, budget, capacity, or PHI. Where `key_aspects`/metadata left `open_questions`, the draft must surface them as explicit gaps, not invented facts.
5. **Supabase is the source of truth** for drafts and evaluations. No TinyDB/JSON for these entities.
6. **Status vocabulary — consistent with CONTEXT §2.3.** Two distinct levels; do not conflate them, and do not use hyphens.
   - **Ticket status (`Ticket.status`) uses ONLY the CONTEXT §2.3 values, verbatim.** Full ticket lifecycle: `analyzing` → `discarded` | `intake_complete` (Part 1) → `drafting` → `under_evaluation` (Part 2) → `waiting_for_approval` → `done` (Part 3). **Phase 2 introduces no new ticket status.** In Phase 2 the ticket is `drafting` (generators writing first-pass sections) then `under_evaluation` (generator↔evaluator loop). **At Phase 2 completion the ticket remains `under_evaluation`** — advancing to `waiting_for_approval`/`done` is Part 3’s job (out of scope). Never set a Part-3 status here.
   - **Section status (`DepartmentSection.status`)** is a finer-grained field the task mandates: `drafting` (with the generator), `under_evaluation` (with the evaluators), `passed` (evaluation cleared), `needs_human_review` (iteration limit hit or PHI hard-stop). It reuses the CONTEXT `drafting`/`under_evaluation` words at section scope; `passed` and `needs_human_review` are **section-level Phase-2 extensions not in CONTEXT §2.3** — record them in `decisions.md`. `passed` sections feed Part 3’s approval flow (`approval_status` column), which stays untouched here.
   - **Rollup indicators (`sections_needing_review` count, `phase2_complete` flag) are derived booleans/counts, NOT status values** — they never appear in `Ticket.status` or `DepartmentSection.status`.
7. **Do not implement Part 3** (approvals, arbitration, final document). Leave `approval_status`/`approver`/`approved_at` untouched.

---

## 5. Detailed Requirements

Layout — extend the Phase 1 pipeline package (keep routers thin; agent logic lives in the pipeline):

```
data/pipelines/rfp_intake/
  agents/
    generator.py       # per-department section generator
    evaluators/
      __init__.py
      readability.py    # readability evaluator (wraps the Phase 1 metrics wrapper)
      relevance.py      # relevance evaluator (LLM)
      compliance.py     # compliance evaluator (rules + PHI, LLM-assisted)
      aggregate.py      # single-writer join → EvaluationResult
  drafting_graph.py     # LangGraph loop: generate → fan-out evaluate → aggregate → route
  drafting_state.py     # DraftingState TypedDict (per-section)
  drafting_runner.py    # entrypoint invoked by the start-drafting BackgroundTask + __main__ CLI
  rules.py              # compliance rule catalog (rule_ids + predicates) — see §5.4
  repository.py         # EXTEND: upserts for draft_content + EvaluationResult + statuses
```

### 5.1 Trigger (Phase 1 → Phase 2): explicit "Start drafting" button

Phase 2 is **started manually by sales**, not auto-chained. A ticket sits at `intake_complete` after Phase 1 until a user acts.

- **UI:** in the backoffice ticket list/detail (`uis/backoffice/rfp-intake/`), every ticket whose status is `intake_complete` shows a **"Start drafting"** button next to it (after the reviewer has read the Phase 1 `key_aspects` / sales summary). The button is only rendered/enabled for `status == intake_complete`.
- **Endpoint:** `POST /api/v1/rfp-intake/tickets/{ticket_id}/start-drafting` (behind `Depends(get_current_user)`, matching the other rfp-intake routes). The handler:
  1. Validates the ticket is `intake_complete` (reject with `409` otherwise — guards double-clicks / wrong-state calls, and makes the action **idempotent**: a ticket already `drafting`/`under_evaluation` returns its current state rather than starting a second run).
  2. Creates a `JobRun` (`job_name="rfp_drafting"`, keyed by `ticket_id`), sets `Ticket.status = drafting`, and schedules `drafting_runner` in a FastAPI `BackgroundTask`.
  3. Returns `202 Accepted` with `{ ticket_id, status: "drafting" }`; the UI then polls section statuses.
- The runner starts one loop per `DepartmentSection`.
- **Also expose:** `POST /api/v1/rfp-intake/tickets/{ticket_id}/redraft` (re-run a single section after human review) and a `drafting_runner.py __main__` CLI guarded on `DATABASE_URL`, mirroring Phase 1 §8.5.

### 5.2 Generator agent (`generator.py`) — one invocation per department

- **Input** (typed — see §8.1): `department_id`, the department's `key_aspects` (Phase 1), shared metadata (`client_name`, `client_country`, `program_type`, `covered_population`, `deadline`, `budget_range`, currency implied by country), the department's `open_questions`, and — on a retry — the prior `draft_content` + `feedback_for_generator`.
- **Output:** `draft_content` (markdown) for **its own** section only. Country-aware: a US section must include a BAA clause, a UK section a DPA/UK GDPR clause; pricing in the country's currency (so the compliance evaluator passes on the first try where possible).
- **Never invents data** (§4.4): unresolved `open_questions` are written as explicit "Open items / to confirm" bullets, not fabricated figures.
- Sets `section.status = drafting` on entry; writes `draft_content` to the section (Supabase) on completion.
- Uses the LLM-proxy convention; department-specific system prompts (revenue = financial terms/currency; clinical = feasibility/capacity/sites; compliance = regulatory posture, BAA/DPA, no PHI).

### 5.3 Evaluator agents — run in **parallel**, then aggregate

All three receive the **same** evaluator input (§8.1) and each writes **only its own** result key (§8.2). None writes to Supabase directly — the aggregate node is the single writer.

1. **Readability evaluator (`readability.py`):** compute metrics via the Phase 1 `py-readability-metrics` wrapper on `draft_content`. `pass` when the score meets the configured threshold (default: Flesch-Kincaid grade ≤ `RFP_READABILITY_MAX_GRADE=12`; also report Flesch Reading Ease). Emit `{ pass, score, details }` where `details` names the metric(s) and the threshold. If the tokenizer is unavailable, degrade to `pass=true` with `details.status="unavailable"` (do not fail the whole loop on infra).
2. **Relevance evaluator (`relevance.py`):** LLM check that `draft_content` **answers the department's "question"** — i.e. covers the department's `key_aspects` and subtask. Returns `{ pass, missing_aspects[] }` where `missing_aspects` are the specific key_aspects/subtask items not addressed. `pass` when `missing_aspects` is empty (or below a configured tolerance).
3. **Compliance evaluator (`compliance.py`):** evaluate `draft_content` against the CONTEXT §5 guideline set encoded in `rules.py` (§5.4). Returns `{ pass, rule_ids[], violations[] }` — `rule_ids` = all rules evaluated, `violations` = `[{rule_id, message}]` for failures. **Mandatory PHI check first:** if PHI is detected (reuse the Phase 1 detectors), set `contains_phi=true`, mark the `phi-free` rule violated, and signal the **hard-stop** path (§8 decision) — do not merely fail-and-loop. Also sets the `evaluation_results.contains_phi` flag on the section.

**Aggregate node (`aggregate.py`) — single writer:** joins the three result keys once all complete, computes `overall_pass = readability.pass AND relevance.pass AND compliance.pass` (PHI hard-stop forces `overall_pass=false` and routes to human review regardless), composes the **specific** `feedback_for_generator` (§8.4), and performs the **only** Supabase write of the `EvaluationResult` + section status for that iteration.

### 5.4 Compliance rule catalog (`rules.py`)

Encode CONTEXT §5 as addressable rules so violations are precise and feedback is actionable. Minimum set:

| `rule_id` | Rule | Fires when |
| --- | --- | --- |
| `phi-free` | No patient identifiers / PHI (mandatory) | any PHI detected → **hard stop** |
| `baa-required-us` | US client section includes a BAA clause | `client_country==US` and no BAA clause present |
| `dpa-required-uk` | UK client section includes a DPA / UK GDPR clause | `client_country==UK` and no DPA/UK-GDPR clause present |
| `currency-usd-us` | US pricing quoted in USD | `client_country==US` and non-USD currency used |
| `currency-gbp-uk` | UK pricing quoted in GBP | `client_country==UK` and non-GBP currency used |
| `no-invented-figures` | No fabricated headcount/budget beyond metadata | figures appear that contradict / exceed metadata + open_questions |

Clause/currency detection may combine deterministic checks (regex/keyword for "Business Associate Agreement", "Data Processing Agreement", currency symbols) with an LLM judgment for nuance; PHI is deterministic-first (detectors), LLM only as a secondary signal — never LLM-only for PHI.

### 5.5 Loop controller (`drafting_graph.py`)

- Per-section conditional edge after aggregate: `passed` → exit (`section.status=passed`); `failed & iterations<limit` → back to generator with feedback, increment `iteration`, `section.status=drafting`; `failed & iterations>=limit` → keep draft+result, `section.status=needs_human_review` (§8.3); `phi` → immediate `needs_human_review` + Compliance flag (bypass remaining iterations).
- **Iteration limit:** `RFP_MAX_DRAFT_ITERATIONS=3` (configurable via settings). Count = number of generate→evaluate cycles. Persist the current `iteration` on the section so re-runs and the UI can show progress; persist an **iteration history** (list of prior EvaluationResults or at least their summaries) so reviewers see why it stalled.
- **Section independence & rollup (§8.3):** the three sections loop independently (LangGraph fan-out or independent runner invocations); a `needs_human_review` section does **not** block others (non-blocking, per decision). `Ticket.status = under_evaluation` while any loop is active **and remains `under_evaluation`** once every section ∈ {`passed`,`needs_human_review`} — Phase-2 completion is signaled by the **derived** `phase2_complete` flag + `sections_needing_review` count (§4.6), **not** by a new status. Never advance `Ticket.status` to a Part-3 value (`waiting_for_approval`/`done`).
- **Failure mid-way / crash:** same durability as Phase 1 §8.5 — `JobRun` → `failed` on exception with truncated error; section left in its last persisted status; upserts keyed by (`ticket_id`,`department_id`) make re-runs idempotent; reuse `reclaim_stale_locks`/`has_processing_lock`.

### 5.6 Backoffice UI (`uis/backoffice/rfp-intake/`) — extend Phase 1

- **Start-drafting control:** on the ticket list/detail, tickets at `intake_complete` render a **"Start drafting"** button that calls the §5.1 endpoint; after a `202` the UI switches the ticket to `drafting` and begins polling. Hide/disable the button for any other status (show `drafting`/`under_evaluation` progress instead). Guard against double-clicks (disable on submit).
- Ticket detail: per department show `section.status` (drafting / under_evaluation / passed / needs_human_review), the current `draft_content` (redacted preview only if `contains_phi`), the latest `EvaluationResult` (readability score, missing_aspects, compliance violations with `rule_ids`), the `iteration` count vs. limit, and `feedback_for_generator`.
- **`needs_human_review` surfacing (§8.3):** a clear banner/badge at ticket and section level ("N section(s) need human review"), the retained draft + failing EvaluationResult + iteration history, and the reason (top violations / missing aspects / PHI). Provide a "re-draft this section" action calling the redraft endpoint (for after a human edits inputs). Never render raw PHI.
- Poll section statuses so the reviewer sees `drafting → under_evaluation → passed/needs_human_review`.
- Follow `AGENTS.md` §2 (`.agents/rules/frontend/*`) before UI work.

---

## 6. PHI handling (Phase 2)

Reuse the Phase 1 `phi.py` adapter. In Phase 2 the risk surface is **generated** content: a generator could echo PHI that slipped through, or hallucinate patient-shaped text. Therefore:
1. The compliance evaluator runs the PHI check on every `draft_content`, every iteration, **before** other rules.
2. PHI detected → `contains_phi=true`, `phi-free` violated, `overall_pass=false`, **hard stop** to `needs_human_review` + Compliance (Claire Whitfield) flag; the offending draft is **redacted** before it is persisted or shown, and is **not** fed back to the generator for another attempt (avoids amplifying PHI). Target: 100% PHI block before a section is marked `passed` (CONTEXT §3).
3. No raw PHI in `EvaluationResult`, logs, or UI — store redacted previews and rule violations only.

---

## 7. Data Model (Supabase / SQLModel)

Reuse `Ticket` and `DepartmentSection` (Phase 1 §7). Add Phase-2 persistence:

- **`EvaluationResult`** — persist one per section per iteration (either a dedicated table or an append to `DepartmentSection.evaluation_results` JSON; a **table is recommended** for iteration history + querying KPIs). Shape (matches the task):
  ```
  EvaluationResult:
    section_id / department_id          # FK to DepartmentSection
    ticket_id                           # denormalized for rollup queries
    iteration: int
    readability: { pass, score, details }
    relevance:   { pass, missing_aspects[] }
    compliance:  { pass, rule_ids[], violations[] }   # violations: [{rule_id, message}]
    contains_phi: bool
    overall_pass: bool
    feedback_for_generator: string      # concrete + actionable (§8.4)
    created_at
  ```
- **`DepartmentSection`** additions/uses: `draft_content` (text; redacted if PHI), `status` (drafting|under_evaluation|passed|needs_human_review), `iteration` (int), `latest_evaluation_id` (FK, optional). Keep `evaluation_results.contains_phi` in sync.
- **`Ticket`** rollup: a derived `sections_needing_review` count / `phase2_complete` flag (column or computed in the read endpoint).

Timezone-aware `DateTime`, JSON columns via `sa.Column(sa.JSON)`, register in `SQLModel.metadata.create_all` (mirror `reporting_models.py`). No patient-identifier column, ever.

---

## 8. Required Design Decisions (answer in code + PR notes)

### 8.1 Information the evaluator needs ("needed information" contract)
Each evaluator (and the aggregate) receives one typed payload — enough to judge, nothing extra:
```
EvaluatorInput {
  department_id,
  draft_content,                    # the thing under evaluation
  key_aspects,                      # the department's "question" — what the draft must answer (relevance)
  subtask,                          # the orchestrator's per-department instruction (relevance)
  shared_metadata: { client_country, program_type, covered_population, budget_range, currency, ... },
  open_questions,                   # so "unaddressed" ≠ "should have invented"
  compliance_rules,                 # the §5.4 rule catalog scoped to this section (compliance)
  iteration                         # for history / limits
}
```
- **Relevance** needs `key_aspects` + `subtask` (the question) + `open_questions` (so a legitimately-open item isn't scored as missing).
- **Compliance** needs `client_country` + `budget_range`/currency + the rule catalog + PHI detectors.
- **Readability** needs only `draft_content` + the threshold.
Evaluators receive the draft + judging criteria — never other departments' drafts, never raw PHI-bearing source, never the full RFP.

### 8.2 Two evaluators writing to shared state (concurrency)
**Never let two evaluators write the same state key or the same DB row concurrently.** In LangGraph, concurrent fan-out branches that write the same key raise `InvalidUpdateError` unless a reducer merges them. Rule:
- Each evaluator writes its **own dedicated key** (`readability_result`, `relevance_result`, `compliance_result`) — disjoint, so no merge conflict.
- If a single collector key is preferred, give it an **additive/merge reducer** (e.g. `operator.add` on a list, or a dict-merge) keyed by evaluator id — mirror the existing `Annotated[..., operator.add]` pattern in `app/domains/agent/state.py`.
- **Supabase writes happen once, in the single `aggregate` node** after the fan-out joins — evaluators are pure/read-only w.r.t. the DB. This eliminates write races entirely and gives one atomic `EvaluationResult` per iteration.

### 8.3 Iteration limit reached → how it's flagged to sales
- Section → `needs_human_review`; **retain** the last `draft_content` + failing `EvaluationResult` + full iteration history (never discard work).
- **Non-blocking rollup (per decision):** other sections continue; the ticket surfaces `sections_needing_review = N` and stays `under_evaluation` until every section is `passed` or human-resolved. No section blocks another.
- **Sales visibility:** backoffice ticket detail shows a prominent banner + per-section badge with the **reason** (top compliance violations, missing aspects, or PHI hard-stop), the retained draft, and a "re-draft" action. Optionally append a line to the Phase 1 sales summary ("Section <dept> needs human review: <top reason>"). This is the sales-facing flag.

### 8.4 Evaluator feedback: specific, not generic
`feedback_for_generator` must be **concrete and actionable** so the generator can converge within the iteration budget. Compose it from the structured results, naming exactly what to change:
- from relevance: the `missing_aspects[]` to add ("Add coverage of: clinic staffing capacity for 450 employees");
- from compliance: the violated `rule_ids[]` + fix ("Add a BAA clause referencing HIPAA (rule `baa-required-us`); quote pricing in USD not EUR (rule `currency-usd-us`)");
- from readability: the metric + target ("Reduce reading grade from 16.2 to ≤12: shorten sentences in §2").
Generic feedback ("improve the section") is not acceptable — it stalls the loop. PHI is **not** turned into regenerate feedback (hard stop, §6).

---

## 9. Unit Tests — `tests/pipelines/`

Mock all LLM calls (`respx` against `llm.4geeks.ai`); no live network, no real PHI. Cover:

1. **Generator:** produces a section from `key_aspects`; US draft includes a BAA clause + USD, UK draft includes DPA + GBP; unresolved `open_questions` surface as "open items", never invented figures.
2. **Readability evaluator:** pass/fail around the grade threshold; tokenizer-unavailable degrades to `pass` with `details.status="unavailable"`.
3. **Relevance evaluator:** missing key_aspect → `pass=false` with that item in `missing_aspects`; fully-covered draft → `pass=true`; an item that was an `open_question` is **not** reported missing.
4. **Compliance evaluator:** US-without-BAA → `baa-required-us` violation; UK-without-DPA → `dpa-required-uk`; wrong currency → currency rule; clean draft → `pass=true` with populated `rule_ids`.
5. **PHI hard-stop (critical):** a draft containing the Phase 1 synthetic PHI → `contains_phi=true`, `phi-free` violated, section `needs_human_review` immediately, **no further generator iteration**, draft redacted, no raw PHI in `EvaluationResult`/logs/UI payload.
6. **Aggregate / concurrency:** three evaluator results combine into one `EvaluationResult`; `overall_pass` is the AND; simulate parallel writes and assert no lost update / single DB write per iteration (§8.2).
7. **Loop + iteration limit:** failing section loops with feedback and revises; at limit → `needs_human_review`, draft + result retained, iteration history present; feedback is specific (asserts rule_ids/missing_aspects appear).
8. **Rollup / non-blocking:** one section `needs_human_review` while others reach `passed`; ticket shows `sections_needing_review=1`, stays `under_evaluation`, other sections unaffected.
9. **Start-drafting trigger + failure:** `POST /start-drafting` on an `intake_complete` ticket enqueues `rfp_drafting` and sets `drafting`; the same call on a non-`intake_complete` ticket returns `409` and starts no second run (idempotent); simulated exception in the run → `JobRun=failed`, section left in last status, re-run idempotent.

Follow `tests/pipelines/test_pipeline.py` conventions (repo-root pytest, `pythonpath=["services/api","."]`).

---

## 10. Dependencies

**No new Python packages.** Reuse `py-readability-metrics` (+`punkt` handling) and the PHI detectors added in Phase 1. If Phase 1 did not add them, add per SPEC1 §11 first. Frontend: no new deps beyond the existing Next.js app.

---

## 11. Development Workflow

1. `git checkout feature/rfp-intake && git pull` → `git checkout -b feature/rfp-response-generation`.
2. Per `AGENTS.md`: read `memory-bank/{projectbrief,techContext,progress,conventions,decisions}.md` and applicable `.agents/rules/*` (frontend rules for `uis/`) before building.
3. Build order: `EvaluationResult` model + `DepartmentSection`/`Ticket` additions → `rules.py` → generator → three evaluators → aggregate (single writer) → `drafting_graph` loop + limit → start-drafting endpoint + redraft endpoint → backoffice panels (incl. "Start drafting" button) → tests.
4. Keep the CX agent graph untouched; extend only `data/pipelines/rfp_intake/`.
5. Run `uv run pytest tests/pipelines -q` + touched frontend lint/build before proposing a commit. Per `AGENTS.md` §3 update `memory-bank/progress.md` + `decisions.md` (record the new `passed`/`needs_human_review` statuses and the §8 decisions) and **request developer acknowledgement before committing**.
6. PR description: §3 availability check, the four §8 decisions, PHI hard-stop behavior, and what was validated vs. residual gaps.

---

## 12. Acceptance Criteria (Phase 2 "done")

- [ ] A "Start drafting" button on `intake_complete` tickets calls `POST /tickets/{id}/start-drafting`, which moves the ticket to `drafting` (idempotent; `409` on wrong state); a per-department generator then writes `draft_content` from `key_aspects` (country-correct BAA/DPA + currency; no invented data).
- [ ] Three evaluators (readability, relevance, compliance) run **in parallel** and are aggregated into one `EvaluationResult` matching the task's shape (incl. `overall_pass` + concrete `feedback_for_generator`), written once per iteration.
- [ ] Section is `drafting` with the generator and `under_evaluation` with the evaluators; failing sections loop back with **specific** feedback and revise.
- [ ] Iteration limit enforced; at the limit the draft + EvaluationResult are retained and the section is `needs_human_review`, surfaced to sales in the backoffice (non-blocking; other sections proceed).
- [ ] PHI in any draft is a hard stop → `needs_human_review` + Compliance flag, redacted, never looped, never leaked to DB/logs/UI.
- [ ] Concurrency-safe: no lost updates from parallel evaluators; single atomic `EvaluationResult` write per iteration (§8.2).
- [ ] Mid-way failure marks `JobRun=failed`, leaves sections in their last status, re-runnable; Part 3 columns untouched.
- [ ] `tests/pipelines/` covers §9; `uv run pytest tests/pipelines` passes.

---

## 13. Open Clarifying Questions (resolved + still-open)

**Resolved with the requester:**
- Scope → **backend + backoffice UI**. ✔
- PHI in a draft → **immediate hard stop** to `needs_human_review` (no loop). ✔
- Iteration-limit rollup → **non-blocking**; ticket flagged, other sections continue. ✔
- Phase 2 start → **explicit "Start drafting" button** on `intake_complete` tickets (sales-triggered; not auto-chained). ✔

**Recommend confirming (defaults noted, won't block a first pass):**
1. **Iteration limit value** — default `RFP_MAX_DRAFT_ITERATIONS=3`. Confirm the number.
2. **Readability pass threshold** — default Flesch-Kincaid grade ≤ 12 (business/professional reading). Adjust if a different target audience is intended.
3. **Relevance tolerance** — default `missing_aspects` must be empty to pass. Allow a soft threshold (e.g. ≤1 minor aspect) if desired.
4. **`EvaluationResult` storage** — default a **dedicated table** (better history/KPIs) vs. appending to `DepartmentSection.evaluation_results` JSON. Confirm.
5. **Section drafting concurrency** — default: sections drafted **concurrently** (independent loops). If LLM rate limits are a concern, run them sequentially; behavior/results are unchanged either way.

---

## 14. Suggested Additional Tasks (improve outcomes)

1. **Deterministic-first compliance checks** for BAA/DPA/currency (regex/keyword) with the LLM only for nuance — cheaper, more reliable, and makes `rule_ids` exact; keep PHI deterministic-first always.
2. **Few-shot the generators** with a country-correct model section (US w/ BAA+USD, UK w/ DPA+GBP) so first-pass drafts pass compliance more often → fewer iterations, lower cost.
3. **Structured outputs (JSON schema / function-calling)** for evaluators if the proxy supports it, to make `missing_aspects`/`violations` reliably machine-readable; keep the fenced-JSON fallback.
4. **Loop-convergence telemetry / evals** — track iterations-to-pass, `needs_human_review` rate, and PHI-block rate (CONTEXT §3 KPIs) via the `data/eval/` pattern; guards against a feedback style that doesn't converge.
5. **Feedback quality guard** — assert `feedback_for_generator` references concrete `rule_ids`/`missing_aspects`; reject empty/generic feedback in the aggregate node.
6. **Idempotent re-draft** — the redraft endpoint should reset only the target section's loop, preserving other sections and prior iteration history.
7. **`data/pipelines/rfp_intake/README.md` update** — document the drafting graph, the fan-out/aggregate concurrency rule, the loop/limit, and the sales-triggered start-drafting flow.
8. **Golden draft fixtures** (post-generation, PHI-free) for the three departments so evaluator tests don't depend on live generation.

---

## 15. Suggested Models

Route everything through the existing proxy (`settings.generation_model`, default `deepseek/deepseek-v4-flash`) — **no new SDKs**; only the `model` string changes. Recommendations by role:

1. **Generators** — the default flash model is adequate for structured section drafting at temperature ~0.2. For higher first-pass compliance/quality (fewer loops), a **Sonnet-class** model is a strong upgrade — latest **Claude Sonnet 5** (`claude-sonnet-5`). Make it configurable (`rfp_generator_model`).
2. **Relevance & compliance evaluators** — favor strong instruction-following and reliable JSON; a **Sonnet-class** model (`claude-sonnet-5`) is the best fit for judging coverage and regulatory clauses. The **readability evaluator uses no LLM** (pure metrics).
3. **PHI decisioning** — enforced by the deterministic detectors (§6), **not** the LLM; model choice never relaxes the PHI guarantee. An LLM may only add a secondary signal.
4. **Cost/quality knob** — default all nodes to `generation_model`; per-node overrides (`rfp_generator_model`, `rfp_evaluator_model`) let you raise quality only where it moves iterations-to-pass. Anthropic's current families: Claude 5 (`claude-opus-5`, `claude-sonnet-5`, `claude-fable-5`) and Haiku 4.5 (`claude-haiku-4-5-20251001`).
