# Telemetry — Phase 4 (Report) — Build Spec

> Instructions for a coding agent. Reconciles `telemetry_report_screenshot.md`,
> `telemetry_report_readme.md`, and `telemetry_report_context.md` against the codebase.
> Builds the analysis pipeline + `GET /telemetry/report` over the `telemetry_events` table from Phase 3.
> Metrics implement the reconciled KPIs from `telemetry_design_specs.md` (no "emergency"/threshold metrics).

---

## 1. Overview

- `services/api/app/domains/telemetry/analysis.py` — pure, independent metric functions (Pandas).
- `GET /api/v1/telemetry/report` in the telemetry router — resolves the date window, calls the metric
  functions, caches the result (60s TTL), returns `{ "period": {...}, "metrics": {...} }`.

## 2. Tech stack / ground truth

- Data source: `telemetry_events` in Supabase, read via the existing SQLModel `supabase_engine`
  (`app/core/db.py`). Use a repository/query helper that issues parameterised SQL (`session.exec` /
  `sqlalchemy.text`) filtering `event_type` and `timestamp` **in SQL**.
- Fixed columns available: `id, timestamp, service, event_type, level, value, tags(jsonb)`.
  Dimensions like `clinic_id`, `jurisdiction`, `consumption_type` live inside `tags` (extract in Pandas).
- Pipeline order (mandatory): `load (SQL) → refine (Pandas) → convert types → group → aggregate → to_dict`.

## 3. Reconciled metrics (implement all three — one per KPI from Phase 1)

The context doc's `emergency_dispensing_per_day` is **replaced** (no emergency data exists). Implement:

> **Traceability (eval criterion 9):** each metric function's docstring must name (a) the Phase 1
> `telemetry-plan.md` KPI it answers and (b) the original `telemetry_report_context.md` metric it replaces,
> so a grader comparing against the CONTEXT doc sees the mapping. Namely:
> `consumption_volume_per_day` → KPI 1, replaces CONTEXT `dispensing_volume_per_day`;
> `waste_rate_per_day` → KPI 2, replaces CONTEXT `emergency_dispensing_per_day` (no `emergency`/`clinical_context` in code);
> `insufficient_stock_failures_per_day` → KPI 3, the observable stock-out signal.

### `consumption_volume_per_day(start_date, end_date) -> list[dict]`  → KPI 1 (consumption rate)
- SQL: `event_type = 'supply_consumption_created'` AND `timestamp >= start AND timestamp < end` (UTC).
- Pandas: extract `clinic_id`, `jurisdiction` from `tags`; drop rows where either is null.
- `pd.to_datetime(df['timestamp'], utc=True)`; `df['date'] = df['timestamp'].dt.date`.
- `groupby(['date','clinic_id','jurisdiction'])['id'].count()` → rename to `count`.
- Rows: `{ "date","clinic_id","jurisdiction","count" }`.

### `waste_rate_per_day(start_date, end_date) -> list[dict]`  → KPI 2 (waste rate)
- SQL: `event_type = 'supply_consumption_created'` in the window.
- Pandas: extract `jurisdiction` and `consumption_type` from `tags`; drop null-jurisdiction rows;
  derive `is_waste = consumption_type == 'expiry_waste'`.
- Convert timestamp; group `['date','jurisdiction']`; `waste_rate = is_waste.sum() / count` (values in `[0.0,1.0]`).
- Use Pandas aggregation only (e.g. `groupby(...).agg(total=('id','count'), waste=('is_waste','sum'))` then compute rate) — **no row loops**.
- Rows: `{ "date","jurisdiction","waste_rate","total" }`.

### `insufficient_stock_failures_per_day(start_date, end_date) -> list[dict]`  → KPI 3 (stock-out rejection rate)
- SQL: `event_type = 'supply_consumption_failed'` in the window.
- Pandas: extract `jurisdiction` (and optionally `error_code`); drop null-jurisdiction rows.
- Convert timestamp; `groupby(['date','jurisdiction'])['id'].count()` → `count`.
- Rows: `{ "date","jurisdiction","count" }`.

### Additional — `auth_failure_rate(start_date, end_date) -> list[dict]` (if auth was instrumented)
- SQL: `event_type IN ('user_login_succeeded','user_login_failed')` in one query, in the window.
- Pandas: extract `jurisdiction` from `tags` where available; group `['date','jurisdiction']`;
  `failure_rate = failed / (failed + succeeded)`.
- Rows: `{ "date","jurisdiction","failure_rate" }`. Segment per jurisdiction (never a combined rate) — CCO requirement.

**Function rules (all):** accept `start_date`/`end_date` (computed by the endpoint), be pure/side-effect-free
(no DB writes, same inputs → same outputs), filter `event_type` + `timestamp` in **SQL** (never Pandas), convert
timestamps with `pd.to_datetime(..., utc=True)` **before** any groupby, and use only Pandas aggregations
(`.count()/.sum()/.mean()/.agg()`) — no `for` loops over rows. Return `[]` (not an error) for empty periods.

## 4. `GET /api/v1/telemetry/report` endpoint

- Optional query params `start_date`, `end_date` (ISO 8601). Defaults: `end_date = now (UTC)`,
  `start_date = now - 7 days`. **The endpoint owns the window** — resolve once, pass both into every metric
  function; metric functions never apply their own default. Bounds are **inclusive start, exclusive end**.
- Response:
  ```json
  {
    "period": { "from": "<ISO>", "to": "<ISO>" },
    "metrics": {
      "consumption_volume_per_day": [...],
      "waste_rate_per_day": [...],
      "insufficient_stock_failures_per_day": [...],
      "auth_failure_rate": [...]
    }
  }
  ```
  Include `auth_failure_rate` only if auth events were instrumented (Phase 2).
- **Cache:** in-memory dict keyed by the normalised `(start_date, end_date)` with a **60-second TTL**. On hit
  within TTL, return the cached payload without re-running the pipeline. Put the helper in
  `app/domains/telemetry/cache.py` (or inline). The pipeline must not run on every request.

## 5. Business constraints

- `clinic_id` and `jurisdiction` come from `tags`, not fixed columns; drop rows where they're null before grouping.
- US and UK always segmented separately — never a combined metric.
- The pipeline touches only `supply_id`, `clinic_id`, `jurisdiction`, `consumption_type`, `error_code`, `event_type`.
  If any `tags` field looks like patient data, stop and escalate — do not include it.

## 6. Dependencies & workflow

- **Add `pandas` to `services/api/pyproject.toml`** (it is not currently a dependency) and run `uv sync` /
  `uv lock` in `services/api/`. No other new packages.
- Prereq data: ≥20 `telemetry_events` rows with varied `event_type` from real backoffice activity (generate via
  the inventory module) before verifying.
- PR: title `[W17D49] Telemetry Report`; description names the (two+) metrics and the business question each
  answers, includes a sample `GET /telemetry/report` JSON with real data, and notes whether `auth_failure_rate` was done.

## 7. Definition of done (maps to `telemetry_report_eval_criteria.md`)

- [ ] `app/domains/telemetry/analysis.py` with ≥2 independent, pure metric functions (this spec defines 3 + optional auth).
- [ ] Each follows `load(SQL) → refine(Pandas) → convert → group → aggregate`; `event_type` + `timestamp` filtered in SQL.
- [ ] `pd.to_datetime(..., utc=True)` before every temporal `groupby`.
- [ ] No loops to compute metrics — Pandas aggregations only.
- [ ] Each function returns a JSON-serialisable `list[dict]` with a grouping dimension (not a global scalar).
- [ ] `GET /api/v1/telemetry/report` with optional dates, 7-day default, `{ period, metrics }` shape.
- [ ] 60s in-memory TTL cache; pipeline not recomputed per request.
- [ ] Metrics map to the three reconciled KPIs from `telemetry_design_specs.md`.
