# SPEC — RFP Intake, Phase 3 (Milestone 9, Part 3): Approvals, Arbitration & Final Document

> **Audience:** the coding agent implementing this feature.
> **Source of truth for domain rules:** [`CONTEXT-multi_agent.md`](./CONTEXT-multi_agent.md) — read it in full, especially §2.1 (owners), §5 (guidelines), §6 (Part 3 deliverable), and §7 (conflict triggers & fixed arbiter).
> **Prior work:** [`SPEC-rfp-intake-phase1.md`](./SPEC-rfp-intake-phase1.md) + [`SPEC-rfp-intake-phase2.md`](./SPEC-rfp-intake-phase2.md). Phase 3 **extends** them; reuse their models, statuses, module layout, LLM convention, PHI detectors, and the Phase 2 generator↔evaluator loop. Do not re-implement them.
> **Repo:** `chitrasharath_healthcore_ft_ai_1/` (the HealthCore monorepo).
> **Base branch:** `feature/rfp-response-generation` (Phase 2 implemented) → **new work branch:** `feature/rfp-approval-completion`.

---

## 1. Project Overview

This is the **final phase**. Phase 1 produced a validated `Ticket` with per-department `key_aspects`; Phase 2 produced evaluated, `passed` draft sections per department. **Phase 3 takes passed sections through per-department human approval, resolves cross-department conflicts via a deterministic arbiter, and — once every required department (Compliance always) has approved and no section contains PHI — generates the consolidated final document and closes the ticket.**

Phase 3 introduces **human-in-the-loop interrupts**: before a department's section is approved, the graph **pauses at an interrupt** scoped to that department, persists its state to a **durable checkpoint**, and waits for that department's owner to approve or request changes via the backoffice. The pause **blocks only that department** — other departments continue and can approve while one is interrupted. On resume, human input is validated and the flow continues from the checkpoint. Conflicts (PHI, BAA/DPA mismatch, capacity-vs-population) are resolved by a **dedicated arbitration node with fixed, non-LLM rules** (CONTEXT §7).

### 1.1 Department owners & mandatory Compliance (CONTEXT §2.1, §6)

| `department_id` | Owner (approver) | Approval rule |
| --- | --- | --- |
| `revenue` | Tom Callahan | approves independently |
| `clinical` | Dr. Marcus Reid | approves independently |
| `compliance` | Claire Whitfield | **must always approve before closing** |

Departments approve **independently, without blocking each other** (CONTEXT §6). Do **not** invent hierarchy beyond mandatory Compliance.

### 1.2 End-to-end flow (all three phases; Phase 3 detail)

```
Phase 1: upload → intake_complete    (SPEC1)
Phase 2: "Start drafting" → per-dept generate↔evaluate loop → all sections passed   (SPEC2)
        │
        │  Trigger Phase 3 by either:
        │    (a) "Run Phase 3" button          (stepwise; Phase 2 complete / all sections passed)
        │    (b) "Run all phases" end-to-end  (from RFP PDF upload; auto-chains P1→P2→P3, halts at the human approval phase)
        │    (c) optional mid-pipeline: start-drafting?continue_to_approval=true (P2→P3 only, existing intake_complete ticket)
        ▼  (all required DepartmentSections == passed)
Ticket.status = waiting_for_approval        ── Phase 3 approval graph starts, thread_id = ticket_id
        │
        ▼
[arbitration node]  scan structured state for conflict triggers (deterministic, CONTEXT §7)
        │   conflict? → force request_changes / revision on the named section(s) → re-enter Phase 2 loop
        │              (bounded by RFP_MAX_APPROVAL_ITERATIONS)
        ▼   no conflict
 Per department (parallel, INDEPENDENT):
        ┌─────────────────────────────────────────────────────────────┐
        │  [approval gate: interrupt(dept)]  ── pauses ONLY this dept   │
        │        resume w/ {department_id, decision, approver, reason}  │
        │        ├─ approve  → approval_status=approved, approver, approved_at
        │        └─ reject   → request_changes → revision (Phase 2 loop) → back to arbitration/gate
        └─────────────────────────────────────────────────────────────┘
        │
        ▼  (all required approved  AND  compliance approved  AND  no section contains_phi)
[final document node] consolidate approved sections → FinalDocument (currency by country)
        │
        ▼
Ticket.status = done   (final document persisted + retrievable)
```

---

## 2. Tech Stack (reuse Phases 1–2; one new capability)

Identical stack to Phases 1–2 (FastAPI + SQLModel + Supabase, LangGraph pipeline under `data/pipelines/rfp_intake/`, OpenAI-compatible LLM proxy, JobRun/BackgroundTasks, Next.js backoffice). New for Phase 3:

| Concern | Choice |
| --- | --- |
| **Durable checkpointer** | **`langgraph-checkpoint-postgres`** on the Supabase Postgres (source of truth). Replaces `MemorySaver` for the Part-3 graph so interrupts survive restarts and concurrent tickets. Requires `psycopg`; run the checkpointer's `.setup()` migration once. |
| Human-in-the-loop | LangGraph `interrupt()` + resume via `Command(resume=...)`, **thread_id = ticket_id** (langgraph ≥1.2.9 is installed; verify the exact multi-interrupt resume API in that version). |
| Arbitration | Plain Python node reading **structured state** — **no LLM** (CONTEXT §7). |
| Final document | Markdown consolidation; `FinalDocument` SQLModel row; GET endpoint + backoffice download. |

**LLM usage stays** only where Phase 2 already uses it (generator/relevance/compliance evaluators during revision). Approval, arbitration, resume routing, and consolidation are **deterministic code**, not LLM calls.

---

## 3. Availability Verification (confirm before building)

Phase 3 assumes Phases 1–2 landed. Verify; missing items are earlier-phase gaps to reconcile first.

| Need | From | If missing |
| --- | --- | --- |
| `DepartmentSection` with `status` (incl. `passed`), `draft_content`, `approval_status`, `approver`, `approved_at`, `evaluation_results.contains_phi` | SPEC1 §7 / SPEC2 §7 | add columns |
| Phase 2 generator↔evaluator loop reusable per section | SPEC2 §5 | required for the revision path |
| `EvaluationResult` + compliance rule catalog (`rules.py`) | SPEC2 §5.4/§7 | required for re-evaluation after revision |
| PHI detectors adapter (`phi.py`) | SPEC1 §6 | required for the `phi-detected` trigger |
| `JobRun` state machine + BackgroundTasks pattern | base + SPEC1 §8.5 | present |
| Backoffice `rfp-intake` app + ticket detail | SPEC1/2 | extend for approvals |
| **`langgraph-checkpoint-postgres` + `psycopg`** | **NOT installed** | **add + lock (§10)** |
| **Structured conflict fields** in state (see §5.4): `revenue.covered_population`/`contract_volume`, `clinical.committed_capacity`/`sites`, `compliance.instrument` (BAA/DPA), `contains_phi`, **and the Phase 2 `phi_was_redacted` flag on each section's `EvaluationResult`** (§5.4.1) | partially from SPEC1/2 | **add any missing structured fields** so arbitration is state-driven, not text-parsed |

**New for Phase 3 (build these):** the approval graph + per-department interrupt gates, the Postgres checkpointer wiring, the resume endpoints + input validation, the deterministic arbitration node, the cross-department max-iteration bound, per-node execution logging in state, the `FinalDocument` model + generation + retrieval, Part-3 status transitions, the transition-integrity fixes, and the approval UI.

---

## 4. Constraints (inherit all of SPEC1 §4 + SPEC2 §4, plus Part-3 rules)

1. **Arbitration is deterministic and code-driven — never an LLM, never free-form agent consensus** (CONTEXT §7). Agents may *surface* a conflict (as structured flags); the arbitration node *resolves* it by fixed rules. **Compliance always wins on PHI / regulatory triggers.**
2. **PHI is an absolute hard stop, and Phase 3 is the human-in-the-loop review point for it.** Phase 2 auto-redacts detected PHI and may pass a section forward as scrubbed (see §5.4.1) — **redaction alone is not resolution.** Any section/artifact with `contains_phi:true`, **any section Phase 2 flagged `phi_was_redacted:true`**, or any freshly detected patient identifier triggers `phi-detected`: route to Compliance (Claire Whitfield) for human review, block/force `request_changes`/discard path, and **the final-document node must not run** while any PHI is unresolved (CONTEXT §7, §5, §4.4). No raw PHI in any state field, execution log, checkpoint, message, or the final document — not even illustrative.
3. **Compliance approval is mandatory before closing**, regardless of how many departments are involved (CONTEXT §5, §6). The final document generates **only** when every required department has approved, Compliance among them.
4. **Country-correct instrument & currency** (CONTEXT §5): US → BAA + USD; UK → DPA/UK GDPR + GBP. The `baa-dpa-mismatch` trigger enforces the instrument; currency in the final document follows `client_country`.
5. **Departments approve independently; an interrupt blocks only its own department** (CONTEXT §6). No department's pause may stall another's approval.
6. **Do not invent hierarchy** beyond mandatory Compliance (CONTEXT §6). No approval chains, no extra sign-offs.
7. **Concurrency isolation:** every graph run is namespaced `thread_id = ticket_id`; concurrent tickets must never share a checkpoint (§8.2).
8. **Never invent data** (CONTEXT §2.3): missing volume/capacity → open questions / arbitration, never fabricated figures.
9. **Status vocabulary = CONTEXT §2.3, verbatim** (see SPEC2 §4.6): Phase 3 ticket statuses are `waiting_for_approval` then `done`. `approval_status` (per section) uses `pending` | `approved` | `request_changes`. Do not use hyphens; introduce no new *ticket* status.
10. **Supabase is the source of truth** for approvals, the execution log, and the final document. Checkpoints live in Supabase Postgres via the Postgres checkpointer.

---

## 5. Detailed Requirements

Extend the Phase 1/2 pipeline package:

```
data/pipelines/rfp_intake/
  approval_graph.py     # LangGraph: arbitration → per-dept interrupt gates → join → final document
  approval_state.py     # ApprovalState TypedDict; execution_log: Annotated[list, operator.add]
  approval_runner.py    # start(ticket_id) + resume(ticket_id, decision); thread-config helper; __main__ CLI
  arbitration.py        # deterministic conflict-trigger node (phi / baa-dpa / capacity)
  final_document.py     # consolidate approved sections → FinalDocument markdown (currency by country)
  checkpointer.py       # Postgres checkpointer factory (Supabase) + thread_config(ticket_id)
  node_logging.py       # helper: append {agent,input,output,timestamp} (redacted) to execution_log
  repository.py         # EXTEND: approval_status/approver/approved_at, FinalDocument, execution log
```

### 5.1 Part-3 start (button) & the end-to-end run option → status = `waiting_for_approval`

Phase 3 is **started manually**, mirroring the Phase 2 "Start drafting" button; it also offers a one-click **end-to-end** run. Two entry points:

**(a) "Run Phase 3" / "Send for approval" button (stepwise).** Shown on ticket detail when **Phase 2 is complete** — **every required `DepartmentSection` is `passed`**, no section in `needs_human_review`. UI label **"Run Phase 3"** (Send for approval). Endpoint `POST /api/v1/rfp-intake/tickets/{ticket_id}/send-for-approval` (behind `Depends(get_current_user)`):
1. Validate all required sections are `passed` (else `409`; idempotent — a ticket already `waiting_for_approval`/`done` returns current state, no second run).
2. Set `Ticket.status = waiting_for_approval`, create a `JobRun` (`job_name="rfp_approval"`, keyed by `ticket_id`), start the approval graph in a BackgroundTask under `thread_id = ticket_id`.
3. Return `202`. The graph runs through arbitration to the per-department interrupts, then waits for approvals.

**(b) "Run all phases" end-to-end option (starts from RFP PDF).** A single action that **begins with uploading/selecting the RFP PDF**, then chains Phase 1 (intake) → Phase 2 (drafting + evaluation) → Phase 3 start **automatically**, running **until the flow needs a human** — i.e. it halts at the department **approval interrupts** (the human approval phase). Endpoint `POST /api/v1/rfp-intake/run-all` (multipart PDF; returns `ticket_id`).
- Creates (or SHA-256-reuses) the ticket, stores the PDF under `data/raw/`, runs Part 1; **on `intake_complete`** continues into Part 2; **on all sections `passed`** invokes the same Part-3 start, advancing to `waiting_for_approval` and pausing at the interrupts.
- **Human-stop semantics:** stops at the **first** point requiring a human — normally the approval interrupts, but it **also halts** on Part 1 `discarded` / classifier human review, or if a section hits `needs_human_review` during Phase 2. It never auto-approves and never runs past the interrupts.
- Same durability: **one chained `JobRun`** (`rfp_run_all`) with stage checkpointing (`intake` → `drafting` → `approval`); a crash is re-runnable from the last checkpoint.

**(c) Mid-pipeline continue (optional).** `POST .../start-drafting?continue_to_approval=true` on an existing `intake_complete` ticket chains P2→P3 only (no PDF). Not a substitute for (b).

Paths (a)/(b)/(c) that reach Part 3 converge on the same approval graph and `waiting_for_approval`; **resume/approval is always manual** (§5.3). If any section is `needs_human_review`, the ticket stays `under_evaluation` and approval does not proceed until it is resolved.

### 5.2 Per-department interrupt gate (blocks only its department)

Each required department has an **approval gate node** that calls `interrupt(payload)` where `payload` presents that department's section to its owner: `{ ticket_id, department_id, owner, draft_content (redacted if needed), key_aspects, latest EvaluationResult summary }`. The gate pauses **that branch only**.

**Independence pattern (make `interrupt` per-department, version-robust):** the gate's resume value carries a `department_id`; a gate proceeds **only when the resumed decision targets its own `department_id`**, otherwise it re-`interrupt`s (stays paused). This guarantees that resuming with department B's decision advances B while department A's gate re-pauses — "blocks only its respective department" holds regardless of whether the installed LangGraph resumes interrupts individually or collectively. Verify against langgraph ≥1.2.9's interrupt/`Command(resume=...)` semantics and prefer targeting the specific interrupt id when available.

### 5.3 Resume: validate human input, then route

Expose `POST /api/v1/rfp-intake/tickets/{ticket_id}/departments/{department_id}/decision` (behind `Depends(get_current_user)`). Body: `{ decision: "approve" | "reject", approver, reason? }`.

**Validate before resuming (reject with 400/409 on failure):**
- `ticket` is `waiting_for_approval`; `department_id` is a required department for this ticket.
- `decision` ∈ {`approve`,`reject`}; `reason` required when `reject`.
- `approver` matches the department owner in §1.1 (owner-of-record; do not accept approvals from the wrong owner).
- the department's gate is actually **pending** (not already approved / not mid-revision) — idempotent: a duplicate approve returns current state, not a second resume.

Then resume the graph: `graph.invoke(Command(resume={department_id, decision, approver, reason}), config=thread_config(ticket_id))`. **Routing ("determine where to resume"):** the matching gate reads the decision — `approve` → write `approval_status=approved`, `approver`, `approved_at`, proceed to join; `reject` → `approval_status=request_changes`, route the section into the **revision path** (§5.5). Non-matching gates re-interrupt. After a crash, resume reloads the checkpoint by `thread_id` and continues from the last completed node.

### 5.4 Arbitration node (deterministic, fixed arbiter — CONTEXT §7)

A dedicated `arbitration.py` node runs **before approval gates and again whenever a decision/revision lands**. It reads **structured state fields** (never re-parses prose) and fires triggers in this fixed priority order:

| Order | `trigger_id` | Detect from structured state | Fixed arbiter | Deterministic resolution |
| --- | --- | --- | --- | --- |
| 1 | `phi-detected` | any section `evaluation_results.contains_phi == true`, **`evaluation_results.phi_was_redacted == true` (Phase 2 scrubbed it — §5.4.1)**, or an independent PHI re-scan hits | **Compliance (Claire Whitfield)** | **Hard stop:** route to Compliance human review; redact/block; force `request_changes` (or discard path); final-document node must not run; overrides all other triggers |
| 2 | `baa-dpa-mismatch` | `client_country==US` without BAA, or `==UK` without DPA/UK-GDPR, or wrong instrument for country (`compliance.instrument`) | **Compliance (Claire Whitfield)** | Force `request_changes` on `compliance` (and any section embedding the wrong clause) until country-correct |
| 3 | `capacity-vs-population` | `clinical.committed_capacity` / sites cannot cover `revenue.covered_population` / `contract_volume` | **Revenue (Tom Callahan)**, only **after** Compliance confirms no PHI | Reduce covered population or add sites; force revision on `revenue` and/or `clinical` |

- The node **records** the fired `trigger_id`, arbiter, and forced action into state + Supabase; it does not negotiate. Compliance outranks Revenue; PHI outranks everything.
- Wire the three `trigger_id`s explicitly. Agents/generators must **surface** these as the structured fields above so the node can detect them (add any missing field per §3). If a required structured figure is absent, that is an open question / revision — never invent it.

#### 5.4.1 PHI handoff from Phase 2 — redaction is deferred, not resolved

**Phase 2 does not hard-stop on PHI; it auto-redacts and lets the (scrubbed) section proceed.** In the Phase 2 evaluator, a draft that contained PHI is redacted, and its `EvaluationResult.contains_phi` reflects only **residual** PHI *after* the auto-scrub — so a successfully-scrubbed section reports `contains_phi=false` and reaches `passed` with `phi_was_redacted=true`. This is **intentional**: PHI is treated as a **human-in-the-loop matter that belongs to Phase 3**, where Compliance (Claire Whitfield) reviews and approves. Redaction by Phase 2 is a safety measure, **not** a resolution of the PHI event.

Phase 3 is therefore the authoritative PHI gate and **must not trust Phase 2's residual-clean `contains_phi` flag alone.** The arbitration node’s `phi-detected` trigger fires when **any** of these is true for a section:
1. `evaluation_results.contains_phi == true` (residual PHI Phase 2 could not scrub), **or**
2. `evaluation_results.phi_was_redacted == true` (Phase 2 *did* detect and scrub PHI — the human-review obligation carries forward), **or**
3. an **independent PHI re-scan** in Phase 3 detects identifiers (defense in depth; do not rely solely on Phase 2’s narrower detector, which may miss standalone DOB/MRN/email).

On any of these, route to **Compliance human review** (a `compliance` approval gate / arbiter decision by Claire Whitfield): the owner explicitly **approves the redaction as safe** or **requests changes / discards**. The section is **not** treated as clean just because Phase 2 scrubbed it, and the **final document must not generate** until Compliance has cleared every redacted/flagged section. The UI surfaces `phi_was_redacted` sections with a "PHI redacted — Compliance review required" banner and shows only the redacted preview (never raw PHI). This is the human-in-the-loop step that closes the Phase 2 auto-redact.
- Each forced `request_changes`/revision counts against the §5.6 iteration bound.

### 5.5 Revision path (on reject or arbitration-forced changes) → re-enter Phase 2 loop

Per the chosen design, a section needing changes **re-enters the Phase 2 generator↔evaluator loop**: regenerate with the concrete feedback (approver's `reason` and/or the arbitration `trigger_id` + rule), re-evaluate readability/relevance/compliance, and — on `passed` — return to arbitration → approval gate for re-approval. Section status cycles `passed` → (`request_changes`) → `drafting` → `under_evaluation` → `passed`. PHI in a revised draft remains a hard stop (SPEC2 §6). Every revision cycle increments the approval-loop counter (§5.6).

### 5.6 Maximum iteration on the cross-department loop

Bound the revise↔re-evaluate↔re-approve↔arbitration loop with `RFP_MAX_APPROVAL_ITERATIONS` (default **3**, configurable). Count per section (and expose a per-ticket total). **At the limit:** stop looping, **retain** the last draft + EvaluationResult + arbitration record, set the section to `needs_human_review`, keep `Ticket.status = waiting_for_approval`, and surface it to sales (SPEC2 §8.3 pattern). The final document does **not** generate while any required section is unresolved. Deterministic; never infinite.

### 5.7 Per-node execution logging in state

Every node execution appends one entry to `ApprovalState.execution_log` (an `Annotated[list[dict], operator.add]` reducer, mirroring `app/domains/agent/state.py::trace_steps`) via `node_logging.py`:
```
{ agent: <node/agent name>, input: <redacted input snapshot>, output: <redacted output snapshot>,
  timestamp: <ISO-8601 UTC>, ticket_id, department_id?, trigger_id? }
```
- **Redact PHI** in both input and output snapshots before logging (reuse the detectors); never write raw PHI or raw draft text with PHI to the log. Persist the log to Supabase (and it also rides in the checkpoint).
- This is the audit trail used by the transition-integrity check (§5.9) and the end-to-end consistency test (§9).

### 5.8 Final document generation → status = `done`

When **all required departments are `approved`** (Compliance included) **and no section `contains_phi`** and no section is `needs_human_review`, the `final_document.py` node consolidates the **approved** `draft_content` of each section into a `FinalDocument`:
- Fields (CONTEXT §2.3): `ticket_id`, `sections` (ordered, approved content per department), `currency` (USD if `client_country==US`, GBP if UK), `generated_at`.
- Render a **markdown** document **and a PDF**; persist the `FinalDocument` row (source of truth) and make both **retrievable** via `GET /api/v1/rfp-intake/tickets/{ticket_id}/final-document` (and PDF download path) in the backoffice.
- **UI on `done`:** (1) **auto-download** markdown + PDF once when the ticket first reaches `done`; (2) keep a persistent **Download** button on the ticket detail so users can return later and re-download either/both artifacts.
- Set `Ticket.status = done` **only once the document is persisted and retrievable** ("accessible"). If generation fails, leave `waiting_for_approval` and mark the `JobRun` failed (re-runnable).
- Final PHI gate: re-run the PHI check on the consolidated content immediately before marking `done`; any hit → `phi-detected` hard stop, no `done`. Additionally, **no section that Phase 2 flagged `phi_was_redacted` may enter the final document until Compliance has explicitly cleared it** (§5.4.1) — a redacted-but-unreviewed section blocks `done`.

### 5.9 Transition integrity (fix jumps / inconsistent messages / data loss)

Audit and fix the **Part 1→2→3 transitions** so the same `Ticket` and `DepartmentSection` rows carry through with no loss:
- **No status jumps:** the only legal ticket transitions are `intake_complete → drafting → under_evaluation → waiting_for_approval → done` (+ `discarded` in Part 1). Assert illegal jumps are impossible.
- **No data loss:** `key_aspects` (P1) → `draft_content`/`EvaluationResult` (P2) → `approval_status`/`FinalDocument` (P3) all persist and remain readable; the execution log is continuous across phases (same `ticket_id`).
- **Consistent messages/state:** the checkpoint `thread_id` is the ticket_id across every phase graph invocation; no phase overwrites another's fields; redactions are stable (PHI never reappears).
- Produce fixes for any jump, dropped field, or inconsistent message found, and lock them with the §9 end-to-end test.

### 5.10 Backoffice UI (extend `uis/backoffice/rfp-intake/`)

- **Start controls:** on the **upload surface** show **"Run all phases"** (PDF → P1→P2→P3 → halt at approval, §5.1b). On an `intake_complete` ticket show **"Start drafting"** (Phase 2) and optional continue-to-approval (§5.1c). On a **Phase 2–complete** ticket (all required sections `passed`) show **"Run Phase 3"** (§5.1a / `send-for-approval`). Render each button only in its valid state; disable on submit; then poll.
- **Per-department approval controls:** for a ticket in `waiting_for_approval`, show each department's section (redacted preview if flagged), its `approval_status` (pending/approved/request_changes), the owner (§1.1), and **Approve / Reject** actions (Reject requires a reason) calling §5.3. Reflect that approving one department does not unblock others — each shows its own pending/approved state.
- **Arbitration & review surfacing:** show fired `trigger_id`, the arbiter, and forced changes; show `needs_human_review` escalations with the reason and a re-draft action.
- **Final document:** when `done`, **auto-download** markdown + PDF once, and always show a persistent **Download** button for later re-download; show `currency`. Never render raw PHI.
- Poll ticket + per-department states. Follow `AGENTS.md` §2 (`.agents/rules/frontend/*`).

---

## 6. Data Model (Supabase / SQLModel)

Reuse `Ticket`, `DepartmentSection`, `EvaluationResult`. Add / use:

- **`DepartmentSection`** (use existing Part-1 columns): `approval_status` (`pending`|`approved`|`request_changes`), `approver`, `approved_at`; keep `status` (`passed`/`drafting`/`under_evaluation`/`needs_human_review`) in sync during revision.
- **`FinalDocument`** (CONTEXT §2.3): `ticket_id` (FK, unique), `sections` (JSON: ordered approved content per department), `currency` (`USD`|`GBP`), `generated_at`, plus a `rendered_markdown` text column (or a retrievable path). No PHI columns, ever.
- **Execution log**: `execution_log` entries (a dedicated table keyed by `ticket_id` recommended, or a JSON column) — `{agent, input, output, timestamp, department_id?, trigger_id?}`, redacted.
- **Arbitration record**: persist fired `{trigger_id, arbiter, forced_action, resolved, created_at}` per ticket (table or JSON) for the UI + audit.
- **Checkpoints**: created/managed by `langgraph-checkpoint-postgres` (its own tables via `.setup()`) — keyed by `thread_id = ticket_id`.

Timezone-aware `DateTime`, JSON via `sa.Column(sa.JSON)`, register in `SQLModel.metadata.create_all`.

---

## 7. Interrupt / Checkpoint / Concurrency (core mechanics)

### 7.1 Durable checkpointer
Build the Part-3 graph with the **Postgres checkpointer** (`checkpointer.py` factory over the Supabase engine / `settings.database_url`); run its `.setup()` migration on first use. This replaces `MemorySaver` for this graph so an interrupt survives an API restart and can be resumed later. Do **not** change the CX agent graph's checkpointer.

### 7.2 thread_id namespacing (§8.2)
Every `invoke`/`resume` uses `config = {"configurable": {"thread_id": str(ticket_id)}}` via a single `thread_config(ticket_id)` helper. **Concurrent tickets get distinct threads → distinct checkpoints; they never share state.** Add a test with two tickets interrupted simultaneously proving isolation.

### 7.3 Resume routing
`approval_runner.resume(ticket_id, decision)` loads the thread by `ticket_id` and issues `Command(resume=decision)`; the matching gate advances, others re-interrupt (§5.2). Validate input first (§5.3).

---

## 8. Key Design Decisions (answer in code + PR notes)

1. **Interrupt granularity — one interrupt per department, resume-value matched by `department_id`** (§5.2), so a pause blocks only its department and B can approve while A waits. Prefer targeting the specific interrupt id if the installed LangGraph exposes it.
2. **Concurrency — `thread_id = ticket_id`, durable Postgres checkpointer** (§7); concurrent tickets isolated; single `thread_config` helper used everywhere.
3. **Arbitration — deterministic node over structured state, fixed arbiters, fixed priority** (PHI > BAA/DPA > capacity), Compliance wins on PHI/regulatory (§5.4). No LLM, no consensus.
4. **Resume routing & validation — validate owner/decision/state, then route approve→approved / reject→revision** (§5.3); re-entrant after crash via the checkpoint.
5. **Revision path — re-enter the Phase 2 generator↔evaluator loop** (§5.5); one quality bar; bounded by iterations.
6. **Max cross-department iterations — `RFP_MAX_APPROVAL_ITERATIONS=3`, terminal = `needs_human_review` + escalate**, no final doc while unresolved (§5.6).
7. **Node logging — additive `execution_log` reducer, redacted `{agent,input,output,timestamp}` per node** (§5.7).
8. **Final document — generate only after all approvals (Compliance incl.) + no PHI; `done` when persisted + retrievable; currency by country** (§5.8).

---

## 9. Tests

Mock LLM calls (`respx`); simulate approvals; no live network, no real PHI. Use the SPEC1 synthetic PHI fixture for PHI cases.

**Unit (Phase 3) — `tests/pipelines/`:**
1. **Arbitration triggers:** each of `phi-detected`, `baa-dpa-mismatch`, `capacity-vs-population` fires from the right structured state, names the correct arbiter, and forces the correct action; priority holds (PHI overrides; Compliance beats Revenue).
1b. **Phase 2 redaction handoff (§5.4.1):** a section that Phase 2 marked `phi_was_redacted=true` but `contains_phi=false` still fires `phi-detected` and routes to Compliance human review; the ticket cannot reach `done` until Compliance clears it; an independent Phase-3 re-scan catches a DOB/MRN/email that Phase 2's detector missed.
2. **Interrupt/gate:** a department gate pauses; resuming with that department's decision advances it; resuming with a different department leaves it paused.
3. **Resume validation:** wrong owner, missing `reason` on reject, wrong ticket status, and duplicate approve are rejected/idempotent.
4. **Revision loop + limit:** reject → Phase 2 revision → re-approve; at `RFP_MAX_APPROVAL_ITERATIONS` → `needs_human_review`, no final doc, work retained.
5. **thread_id isolation:** two tickets interrupted concurrently keep separate checkpoints; resuming one does not affect the other.
6. **Node logging:** every node appends a redacted `{agent,input,output,timestamp}`; assert no raw PHI in the log.
7. **Final document:** generates only when all required approved (Compliance incl.) + no PHI; correct `currency` by country; `done` only after retrievable; PHI at final gate blocks `done`.
8. **Compliance-mandatory:** ticket cannot reach `done` without Compliance approval even if Revenue + Clinical approved.

**Required integration / e2e:**
9. **Part-3 e2e with seeded state + simulated approvals:** seed a ticket at all-sections-`passed`, drive the approval graph through arbitration + approvals to `done`, asserting each status transition and the final document content/currency.
10. **Department B approves while Department A is interrupted:** with both gates pending, resume B (approve) and assert B is `approved` while A remains pending/interrupted and the ticket is not yet `done`; then resume A and reach `done`.
11. **Full three-phase run (consistency):** run **≥1 real RFP** (e.g. the Meridian US formal RFP) through Phases 1→2→3 end to end; assert ticket states, the execution-log messages, and all data (`key_aspects`→`draft_content`→`approval_status`→`FinalDocument`) stay **consistent from start to finish**, with no status jump, dropped field, or PHI leak (§5.9).
12. **Interrupt-until / resume-to-completion (end-to-end button):** driving the **"Run all phases"** path (§5.1b) **from an RFP PDF** runs through all three phases, **stops at the department approval interrupts**, and **resumes to completion** on simulated approvals. Also assert it halts on Part-1 discard/human_review or Phase 2 `needs_human_review`.

Follow `tests/pipelines/test_pipeline.py` conventions (repo-root pytest, `pythonpath=["services/api","."]`).

---

## 10. Dependencies

- **Add** `langgraph-checkpoint-postgres` and `psycopg` (binary) to `services/api/pyproject.toml`; `uv lock`; run the checkpointer `.setup()` once (document the migration).
- Reuse everything else (langgraph ≥1.2.9, py-readability-metrics, PHI detectors) from Phases 1–2. No new frontend deps.

---

## 11. Development Workflow

1. `git checkout feature/rfp-response-generation && git pull` → `git checkout -b feature/rfp-approval-completion`.
2. Per `AGENTS.md`: read `memory-bank/{projectbrief,techContext,progress,conventions,decisions}.md` and applicable `.agents/rules/*` before building.
3. Build order: dependencies + Postgres checkpointer → `FinalDocument` model + approval columns + execution-log table → `arbitration.py` (deterministic) → approval graph + per-dept interrupt gates + `thread_config` → start endpoints (`send-for-approval` + `run-all` end-to-end) → resume endpoints + validation → revision path wiring into the Phase 2 loop → max-iteration bound → `final_document.py` + retrieval endpoint → Part-3 status transitions → transition-integrity audit/fixes → backoffice approval UI (Send-for-approval / Run-all / Approve-Reject) → unit tests → integration/e2e tests → full three-phase run.
4. Keep the CX agent graph untouched; extend only `data/pipelines/rfp_intake/`.
5. Run `uv run pytest tests/pipelines -q` + touched frontend lint/build before proposing a commit. Per `AGENTS.md` §3 update `memory-bank/progress.md` + `decisions.md` (record the §8 decisions, the Postgres checkpointer, and the transition fixes) and **request developer acknowledgement before committing**.
6. PR description: §3 availability check, the §8 decisions, the arbitration triggers wired, the transition-integrity findings + fixes, and what was validated (incl. the full three-phase run) vs. residual gaps.

---

## 12. Acceptance Criteria (Phase 3 / Milestone 9 "done")

- [ ] A **"Send for approval"** button (all sections `passed`) and a **"Run all phases"** end-to-end option (**from RFP PDF upload**, chaining P1→P2→P3 and halting at the human approval interrupts) both reach `waiting_for_approval` and start the approval graph under `thread_id = ticket_id` on a **durable Postgres checkpoint**; approval/resume is always manual.
- [ ] Each department has an interrupt before approval that **blocks only its own department**; Department B can approve while Department A is interrupted.
- [ ] Resume **validates human input** (owner, decision, reason, state; idempotent) and **routes** approve→approved / reject→revision; flow resumes correctly after a restart from the checkpoint.
- [ ] The **arbitration node** fires the three CONTEXT §7 triggers deterministically with fixed arbiters (Compliance wins on PHI/regulatory); no LLM/consensus. **A Phase 2 `phi_was_redacted` section is treated as PHI-detected and routed to Compliance human review (§5.4.1); redaction alone never clears the gate.**
- [ ] Rejection/arbitration changes **re-enter the Phase 2 loop**; the cross-department loop is bounded by `RFP_MAX_APPROVAL_ITERATIONS`, terminating in `needs_human_review` (no infinite loop, work retained).
- [ ] **Every node logs** `{agent, input, output, timestamp}` (redacted) into state; no raw PHI in the log.
- [ ] `thread_id` is namespaced by `ticket_id`; concurrent tickets never share a checkpoint (proven by test).
- [ ] The **final document** consolidates approved sections (correct currency), the `FinalDocument` row + rendered markdown are retrievable, and `Ticket.status = done` only when accessible — and only with Compliance approval and no PHI.
- [ ] Transition integrity: no status jumps, no data loss, consistent messages across Parts 1→2→3 (fixes applied).
- [ ] Tests pass: Phase-3 unit tests, the Part-3 e2e with seeded approvals, the **B-approves-while-A-interrupted** test, and the **full three-phase run** confirming end-to-end consistency; `uv run pytest tests/pipelines` green.

---

## 13. Open Clarifying Questions (resolved + still-open)

**Resolved with the requester:**
- Checkpointer → **Postgres / Supabase** (`langgraph-checkpoint-postgres`). ✔
- Revision path → **re-enter the Phase 2 generator↔evaluator loop**. ✔
- Department `reject` → **`request_changes` → revise loop** (bounded; then `needs_human_review`). ✔
- Final-doc "accessible" → **`FinalDocument` row + retrievable markdown** (GET + backoffice); `done` when retrievable. ✔
- Part-3 start → **"Send for approval"** + **"Run all phases" from RFP PDF** (P1→P2→P3) + mid-pipeline `continue_to_approval` (§5.1). ✔

**Locked planning clarifications:**
1. **Part-3 start** — RESOLVED: **"Send for approval"** (stepwise) **plus** **"Run all phases"** starting from **RFP PDF upload** via `POST /run-all` (multipart) chaining P1→P2→P3 **plus** `start-drafting?continue_to_approval=true` for P2→P3 only. ✔
2. **`RFP_MAX_APPROVAL_ITERATIONS`** — RESOLVED: default **3**, **per-section** (per-ticket total exposed). ✔
3. **Final document format** — RESOLVED: **markdown + PDF**; on `done` **auto-download once** + persistent **re-download** button. ✔
4. **Approver identity source** — RESOLVED: validated **name string** vs fixed owners (§1.1); RBAC deferred. ✔
5. **PHI on a rejected/forced-changes section** — RESOLVED: hard stop with **redact option**; `phi_was_redacted` still needs Compliance Approve. ✔

---

## 14. Suggested Additional Tasks (improve outcomes / robustness)

1. **State-machine guard** — a single `can_transition(from,to)` helper enforcing the legal ticket transitions (§5.9), used by every status write, so illegal jumps are impossible by construction (supports the transition-integrity requirement).
2. **Idempotency keys on decisions** — dedupe double-clicked approvals (approver + department + decision) so a repeated POST never double-resumes.
3. **Arbitration + approval telemetry / KPIs** — track approval time per department (special-case Compliance), trigger-fire rates, and iterations-to-close (CONTEXT §3 KPIs) via the `data/eval/` pattern.
4. **Checkpoint GC / retention** — a small job to prune completed tickets' checkpoints so the checkpoint tables don't grow unbounded.
5. **Resume audit endpoint** — `GET /tickets/{id}/timeline` rendering the execution log (redacted) so sales/compliance can see who approved what and when.
6. **Golden final-document fixtures** — a US (BAA/USD) and a UK (DPA/GBP) expected consolidated document to lock formatting + currency + clause presence.
7. **Crash-recovery test** — kill and reload between interrupt and resume, proving the Postgres checkpoint truly restores mid-flow (beyond the in-process resume test).
8. **`data/pipelines/rfp_intake/README.md` update** — document the approval graph, interrupt/resume, thread_id namespacing, arbitration triggers, and the final-document flow.
9. **Deterministic clause/currency detectors** — reuse the Phase 2 `rules.py` predicates in arbitration so `baa-dpa-mismatch` is code-detected, not LLM-judged.

---

## 15. Suggested Models

Phase 3's control flow (interrupts, arbitration, resume routing, consolidation, status) is **deterministic code — no LLM**. The LLM is used **only** on the revision path, which is the Phase 2 loop:

1. **Revision regeneration + relevance/compliance re-evaluation** — same as SPEC2 §15: default `settings.generation_model` (`deepseek/deepseek-v4-flash`); a **Claude Sonnet 5** (`claude-sonnet-5`)-class model is a strong per-node upgrade for regulatory-clause correctness (BAA/DPA) and reliable JSON, via the existing proxy (no new SDK). Keep it configurable (`rfp_generator_model`, `rfp_evaluator_model`).
2. **Arbitration & PHI** — **never** an LLM (CONTEXT §7; PHI is deterministic detectors). Model choice cannot relax any Phase-3 guarantee.
3. **Final document consolidation** — deterministic assembly of already-approved text; no model needed. (If you later want prose smoothing, gate it behind a PHI re-check and keep it optional.)
Anthropic's current families for reference: Claude 5 (`claude-opus-5`, `claude-sonnet-5`, `claude-fable-5`) and Haiku 4.5 (`claude-haiku-4-5-20251001`).
