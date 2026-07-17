---
name: Data Pipeline Design (Part 1)
overview: "Documentation-only phase: author docs/data_pipelines/pipeline-design.md as the sole design artifact for Build 1 and Build 2. No Prefect/SQL/Python ETL code."
todos:
  - id: step0-branch
    content: Create feature/data_pipeline from main; confirm telemetry domain on main matches design ground truth
    status: completed
  - id: step1-baseline-audit
    content: Audit telemetry models/analysis/repository/router, docs/telemetry/telemetry-plan.md, and mapper allowlists against design specs §2
    status: completed
  - id: step2-author-design
    content: Write docs/data_pipelines/pipeline-design.md with all required sections (§3–§5), Build 1 vs roadmap tags, and locked stakeholder decisions
    status: completed
  - id: step3-eval-pass
    content: Checklist against data_pipeline_design_eval_criteria.md and design specs §7 DoD (path = docs/data_pipelines per stakeholder)
    status: completed
  - id: step4-commit
    content: Commit on feature/data_pipeline with message feat: add pipeline design document; pause for review (no Build 1 yet)
    status: completed
isProject: false
---

# Data Pipeline — Part 1 (Design) Implementation Plan

**Plan file:** [`data_pipeline_design_implementation_plan.md`](data_pipeline_design_implementation_plan.md)

**Requirements sources:**

- [`data_pipeline_design_specs.md`](data_pipeline_design_specs.md)
- [`data_pipeline_design_eval_criteria.md`](data_pipeline_design_eval_criteria.md)
- KPI / event ground truth: [`docs/telemetry/telemetry-plan.md`](../../../docs/telemetry/telemetry-plan.md), [`docs/telemetry/event-schemas.json`](../../../docs/telemetry/event-schemas.json), and delivered code under `services/api/app/domains/telemetry/`

**Branch:** `feature/data_pipeline` (created off **`main`**; all three parts land here)

**Deliverable (this phase only):** `docs/data_pipelines/pipeline-design.md` — Markdown design. **No** Prefect flows, SQL migrations, or runnable ETL.

**Status:** **Delivered** — `docs/data_pipelines/pipeline-design.md` on `feature/data_pipeline`. Pause for review before Build 1.

**Downstream plans (later phases):** Build 1 and Build 2 implementation plans will be authored after Design sign-off; both reference **this same** `docs/data_pipelines/pipeline-design.md` (no second design file under `data/pipelines/`).

---

## Executive summary

Today `GET /api/v1/telemetry/report` recomputes four Pandas KPIs from append-only `telemetry_events` on every request (60s cache). HealthCore needs an auditable, idempotent ETL that materializes those KPIs into `reporting_*` tables so `/telemetry/report` reads pre-aggregated rows, with run logging and fail-closed PHI protection.

Part 1 authors the design blueprint another engineer uses for Build 1 (resilient Prefect pipeline + tables + endpoints) and Build 2 (subflows + unit tests) **without redesign**. Vocabulary (flows, tasks, tables, grains, states) is fixed here.

---

## Locked decisions (stakeholder Q&A)

| # | Decision |
|---|---|
| Process | Three separate implementation plans; **pause after every phase** |
| Branch | `feature/data_pipeline` off `main` |
| Design path | **One** doc: `docs/data_pipelines/pipeline-design.md`. Build 1/2 reference this path for run command and consistency. Do **not** create `data/pipelines/PIPELINE_DESIGN.md` |
| KPI source | `docs/telemetry/telemetry-plan.md` + telemetry implementation (not missing `CONTEXT-company.md`) |
| Config (Build 1) | `data/pipelines/config.py` constants; design documents Prefect Block **shapes** (`SupabaseConfig`, `PipelineConfig`) as the intended config contract |
| Flows | Design + Build 1: `telemetry_etl_flow` + thin `backfill_flow(start, end)` |
| Transform | Single `transform_kpi_aggregates` → reuse `build_metrics`; **per-KPI task isolation = roadmap** |
| Checkpoint | Write `checkpoint` for audit (`extract`→`transform`→`load`); **resume = roadmap** |
| PHI allowlist | Union of `EVENT_PROPERTY_ALLOWLIST` keys from `mapper.py` + envelope keys (`eventId`, `sessionId`, `userId`, `schemaVersion`, `requestId`); fail closed → `status=quarantined` |
| Extract event types | **KPI-only** types used by `build_metrics` (not v1.1 abandon/filter events) |
| Quarantine vs analysis | Keep `analysis.py` KPI math; pipeline counts null-grain / invalid rows as `rows_quarantined` |
| Timestamps | Prefer coerce → NaT (Build 1 prepare path / Build 2 tests) |
| Trigger | `POST …/runs/trigger` via FastAPI `BackgroundTasks`; return `{message, run_id}` |
| Non-critical task | `export_snapshot_optional` **required**; must be invoked with **`return_state=True`**; failure → continue + `status=partial` |
| `partial` | Only when non-critical snapshot export fails (critical stages → `failed` / `quarantined`) |
| Manual verify | Live Supabase (`milestone5_inventory`) for Build 1 walkthrough; Build 2 unit tests DB-free |
| uv | Add Prefect on `services/api`; re-lock **both** `services/api/uv.lock` and root `uv.lock` in Build 1 |

### Design ↔ Build 1 consistency (eval #11)

Every resilience item in the design doc must be tagged **Build 1** or **Roadmap**. Build 1 implements only **Build 1** rows so code matches the doc.

**Build 1 (must describe and later code):** watermark + reprocess window · transactional grain upsert · watermark after commit · `pipeline_runs` lifecycle · extract retries + `retry_condition_fn` · transform `cache_key_fn` / `cache_expiration` · non-critical snapshot + **`return_state=True`** · PHI fail-closed · quarantine counts · fail-fast missing `DATABASE_URL` · serve-last-good · `GET /telemetry/report` (materialized) · `GET /telemetry/raw-report` (live) · `GET …/pipelines/runs/latest` · `POST …/runs/trigger` · `config.py` realizing Block field equivalents · thin `backfill_flow`

**Roadmap (document only in Design):** chunked reads · advisory run-lock / concurrency limit · volume/freshness anomaly · checkpoint **resume** · **per-KPI isolation** via separate tasks/`return_state` · savepoints for sub-batch

---

## Eval criteria crosswalk (Design)

| Eval criterion | How this plan satisfies it |
|---|---|
| Design file exists, readable Markdown | `docs/data_pipelines/pipeline-design.md` (stakeholder path; specs path) |
| One concrete business-purpose sentence | Purpose section ties to HealthCore clinic supply / auth ops visibility |
| Mermaid ≥3 stages + real entity names | `telemetry_events` → extract → transform (`build_metrics`) → load → `reporting_*` + `pipeline_runs` |
| Concrete update strategy | Upsert on each KPI grain (not DISTINCT) |
| Idempotency = second run after load failure | Unique `run_id`, transactional upsert, watermark only after committed load |
| Exec log ≥5 fields + type + justification | Full `pipeline_runs` template (§ Interfaces below) |
| ≥2 flows + ≥3 tasks, concrete names | `telemetry_etl_flow`, `backfill_flow`; extract / transform / load (+ optional snapshot) |
| Consistent with company telemetry KPIs | Four KPIs from `telemetry-plan.md` / `analysis.py` grains |

---

## Ground truth (do not invent names)

**Source:** `telemetry_events` / `TelemetryEventRow` — `id`, `timestamp`, `service`, `event_type`, `level`, `value`, `message`, `tags` (jsonb). Append-only. Read via `load_events()`.

**KPI grains (`analysis.py` → reporting tables):**

| KPI key | Grain (upsert key) | Value columns |
|---|---|---|
| `consumption_volume_per_day` | `report_date · clinic_id · jurisdiction` | `count` |
| `waste_rate_per_day` | `report_date · jurisdiction` | `waste_rate`, `total` |
| `insufficient_stock_failures_per_day` | `report_date · clinic_id · jurisdiction · supply_id` | `count`, `attempts`, `rejection_rate` |
| `auth_failure_rate` | `report_date` | `failed`, `succeeded`, `failure_rate` |

**Already decided (encode in design):**

1. Load target = `reporting_*`; `/telemetry/report` reads them (same JSON → no frontend change); live compute preserved as `/telemetry/raw-report`
2. Transform = reuse `analysis.py` / `build_metrics` as-is
3. Prefect = local ephemeral (`python data/pipelines/pipeline.py`); Blocks described for config shape; Supabase via `settings.database_url`
4. Run log = `pipeline_runs`

**Risk to call out:** app skips Supabase work when `DATABASE_URL` unset — design requires fail-fast for pipeline CLI (never silent empty KPIs).

---

## Implementation steps (Design only)

### Step 0 — Branch

```bash
git checkout main && git pull
git checkout -b feature/data_pipeline
```

Confirm on `main`: `services/api/app/domains/telemetry/{models,analysis,repository,router,mapper,cache}.py` and `docs/telemetry/telemetry-plan.md`.

### Step 1 — Baseline audit (read-only)

Verify and note in the design “Current State” section:

- Four KPI functions + `build_metrics` request path + 60s cache
- Silent `dropna` / missing run log / no materialized tables
- Event types and tag shapes from telemetry plan + mapper allowlist
- Dual-root import trap: `data/pipelines/` ↔ `services/api` (document for Build 1)

### Step 2 — Author `docs/data_pipelines/pipeline-design.md`

Create `docs/data_pipelines/` if needed. Required sections (map to specs §3–§5 and eval):

1. **Current State** — four KPIs, `telemetry_events`, recompute-on-request `/telemetry/report`, limitations  
2. **Purpose** — one HealthCore business sentence  
3. **Extraction format** — source, JSONB tags, append-only, nightly + on-demand, watermark on `timestamp`, rough 12-clinic / 2-jurisdiction volume  
4. **Data-flow diagram** — Mermaid ≥3 stages, real names + `pipeline_runs`  
5. **Update / dedup** — upsert on grains above + reprocess-window for late cross-jurisdiction events  
6. **Idempotency** — describe **second run after load-phase failure** (not aspirational wording)  
7. **Execution log** — `pipeline_runs` field table (name · type · audit justification), ≥5 fields  
8. **Prefect mapping** — ≥2 flows, ≥3 tasks, Running/Completed/Failed, Block shapes  
9. **Build roadmap / handoff** — Build 1 vs Build 2; reuse same vocabulary  
10. **Interfaces** — watermark rules, reprocess-window default, reporting table schemas, endpoints, Blocks  
11. **Resilient, Observable, Recoverable** — each item with failure scenario + rationale + **Build 1 | Roadmap** tag (see locked list)  
12. **Repo traps** — uv; Prefect added in Build 1; cross-root imports  
13. **Run command / schedule** — document intended CLI and nightly `0 2 * * *` (Build 1 will keep this section current)

#### Interfaces to pin (prose/tables, not code)

**Watermark**

- `watermark_to` = `now(UTC)` at run start (or explicit `end`)
- `watermark_from` = latest **successful** run’s `watermark_to` **minus reprocess-window**
- First run: configured lookback (state default in design, e.g. 7 days lookback; reprocess-window default **2 days**)

**Reporting tables** (names + grain + values + `run_id` + `updated_at`):

- `reporting_consumption_volume_daily`
- `reporting_waste_rate_daily`
- `reporting_stock_failures_daily`
- `reporting_auth_failure_daily`

**`pipeline_runs` fields (minimum):**  
`run_id (uuid)` · `started_at` / `finished_at (timestamptz)` · `watermark_from` / `watermark_to` · `rows_extracted` / `rows_loaded` / `rows_quarantined (int)` · `status (running|success|partial|failed|quarantined)` · `error_summary (text?)` · `pipeline_version (str)` · `checkpoint (str?)`  

Eval metadata mapping (for Build 1 endpoints): start→`started_at`, end→`finished_at`, records processed→`rows_loaded`, status→`status`, errors→`error_summary`.

**Endpoints**

- `GET /api/v1/telemetry/report` — materialized  
- `GET /api/v1/telemetry/raw-report` — live `build_metrics`  
- `GET /api/v1/telemetry/pipelines/runs/latest`  
- `POST /api/v1/telemetry/pipelines/runs/trigger`  

**Prefect**

- Flows: `telemetry_etl_flow`, `backfill_flow`
- Tasks: `extract_telemetry_events`, `transform_kpi_aggregates`, `load_reporting_tables`, `export_snapshot_optional`
- Blocks (design shape): `SupabaseConfig { database_url }`, `PipelineConfig { event_types, reprocess_window_days, lookback_days, batch_size, pipeline_version }`

**Batch/transaction tradeoff:** choose **one transaction wrapping all four upserts** (atomic load; watermark after commit) — state why vs chunked replay.

**Quality bar:** for Current State, Purpose, Update/dedup, and Idempotency, include brief strong-vs-weak examples in the author’s notes while drafting; keep the committed doc a design (not a tutorial), but those sections must meet the “second run / concrete mechanism” bar in specs §6.

### Step 3 — Verification checklist

- [ ] File exists; design only (no `pipeline.py` / SQL / orchestration committed in this phase)
- [ ] Purpose = one concrete HealthCore sentence
- [ ] Diagram extract→transform→load with real names
- [ ] Dedup = upsert on named grains
- [ ] Idempotency describes second run after load failure
- [ ] Exec log ≥5 fields with name, type, justification
- [ ] ≥2 flows + ≥3 tasks + Blocks shapes
- [ ] Watermark, reprocess-window, reporting tables, run states specified
- [ ] Resilience section: scenario + rationale + Build 1/Roadmap tags
- [ ] Build roadmap / handoff names Build 1 and Build 2 scope
- [ ] KPI/event names match telemetry-plan + `analysis.py`
- [ ] Dual-root import + missing-`DATABASE_URL` risks noted

### Step 4 — Commit and pause

```text
feat: add pipeline design document
```

**Stop.** Do not start Build 1 until stakeholder signs off on `pipeline-design.md`.

---

## Anti-patterns (reject)

- Invented table/entity names instead of § Ground truth vocabulary  
- Diagram with &lt;3 stages or missing real source/destination names  
- Idempotency as a wish without second-run behavior  
- Exec-log fields without types/justifications  
- Single flow/task only; Prefect buzzwords without pipeline-specific names  
- Skipping Current State  
- Bare resilience name lists without scenario/rationale/tags  
- Any ETL/orchestration code in this phase  

---

## Handoff to Build 1 / Build 2 (preview only)

| Phase | Will implement (separate plans after pause) |
|---|---|
| **Build 1** | Prefect flow + tasks, `reporting_*` + `pipeline_runs`, idempotent load, PHI guard, CLI, report/raw-report + pipeline endpoints, commit `feat: implement resilient prefect pipeline` |
| **Build 2** | ≥3 subflows wrapping existing tasks, `tests/pipelines/test_pipeline.py`, pytest path fix, PR to `main`, commit `feat: refactor pipeline into subflows and add unit tests` |

---

## Definition of done (this phase)

- [ ] `docs/data_pipelines/pipeline-design.md` authored per specs §3–§5 and locked decisions above  
- [ ] Design eval criteria covered (with docs path per stakeholder)  
- [ ] Commit on `feature/data_pipeline`: `feat: add pipeline design document`  
- [ ] Stakeholder review complete before Build 1 plan / implementation  
