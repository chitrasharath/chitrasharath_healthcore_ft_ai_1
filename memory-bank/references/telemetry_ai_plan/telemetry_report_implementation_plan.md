---
name: Telemetry Report (Phase 4)
overview: "Pandas analysis pipeline + JWT-protected GET /api/v1/telemetry/report — three reconciled KPI metrics + auth_failure_rate; reads v1.1.0 stored events; supplementary v1.1 metrics out of scope."
todos:
  - id: step0-prereq
    content: Confirm Phase 3 persistence; seed ≥20 telemetry_events incl. v1.1 abandon + filter via backoffice
    status: pending
  - id: step1-pandas-dep
    content: Add pandas to services/api/pyproject.toml; uv sync + re-lock root dev group if needed
    status: pending
  - id: step2-repository
    content: Add telemetry/repository.py — parameterised SQL load by event_type + timestamp window
    status: pending
  - id: step3-analysis
    content: Implement analysis.py — 3 KPI metrics + auth_failure_rate (unchanged by v1.1 design)
    status: pending
  - id: step4-cache
    content: Add telemetry/cache.py — 60s TTL keyed by normalised date window
    status: pending
  - id: step5-report-endpoint
    content: GET /telemetry/report with date params; JWT protection via get_current_user
    status: pending
  - id: step6-tests
    content: Add tests/test_telemetry_report.py — metric shapes, empty window, cache, auth 401
    status: pending
  - id: step7-verify
    content: curl authenticated report JSON; KPI docstrings reference telemetry-plan.md v1.1.0
    status: pending
isProject: false
---

# Telemetry — Phase 4 (Report) Implementation Plan

**Plan file:** [`memory-bank/references/telemetry_ai_plan/telemetry_report_implementation_plan.md`](telemetry_report_implementation_plan.md)

**Requirements source:** [`telemetry_report_specs.md`](telemetry_report_specs.md), [`docs/telemetry/telemetry-plan.md`](../../../../docs/telemetry/telemetry-plan.md) (v1.1.0)

**Branch:** `feature/telemetry` (fourth commit on same branch)

**Working directory:** `services/api/`

**Status:** Not started — no `pandas` dependency, no report endpoint

---

## Executive summary

Phase 4 turns persisted `telemetry_events` rows into **operational metrics** for the three reconciled KPIs in [`telemetry-plan.md`](../../../../docs/telemetry/telemetry-plan.md). Pure Pandas functions load via SQL, aggregate by date/clinic/jurisdiction, and return JSON-serialisable `list[dict]` results.

`GET /api/v1/telemetry/report` is **JWT-protected** with a 60-second in-memory cache.

### v1.1 design alignment (scope boundary)

Design v1.1.0 added two instrumentable events:

| Event | Stored in Phase 3 | In default report? |
|-------|-------------------|-------------------|
| `supply_consumption_form_abandoned` | yes | **no** — supplementary UX signal; supports KPI 3 *interpretation* only |
| `incident_list_filter_applied` | yes | **no** — Patient Experience audit; not a reconciled KPI |

**Phase 4 report response is unchanged** by v1.1 — still four metric keys:

1. `consumption_volume_per_day` → KPI 1
2. `waste_rate_per_day` → KPI 2
3. `insufficient_stock_failures_per_day` → KPI 3
4. `auth_failure_rate` → auth instrumentation

v1.1 rows remain in `telemetry_events` for ad-hoc SQL and future report extensions.

### KPI 3 + form abandon (documentation only)

[`telemetry-plan.md`](../../../../docs/telemetry/telemetry-plan.md) notes that high `supply_consumption_form_abandoned` volume alongside `supply_consumption_failed` suggests UX/stock friction. The report endpoint does **not** add a `form_abandon_rate` metric in this phase — operators compare via SQL if needed:

```sql
SELECT event_type, count(*) FROM telemetry_events
WHERE event_type IN ('supply_consumption_form_abandoned', 'supply_consumption_failed')
GROUP BY event_type;
```

---

## Planning decisions (locked)

| Topic | Decision |
|-------|----------|
| Design doc | [`telemetry-plan.md`](../../../../docs/telemetry/telemetry-plan.md) v1.1.0 — KPI definitions authoritative |
| Report metrics | **4 keys** — 3 KPIs + `auth_failure_rate`; no v1.1 metric functions |
| Data source | `telemetry_events` on `milestone5_inventory`; `tags.schemaVersion` may be `1.1.0` |
| `tags` dimensions | KPI metrics use `clinic_id`, `jurisdiction`, `consumption_type`, `error_code` from `tags` |
| v1.1 `tags` fields | `filter_dimension`, `abandon_trigger`, etc. — stored but not read by Phase 4 pipeline |
| Auth on report | JWT required |
| Auth on ingest | Public |
| Cache | 60s TTL |
| Tests | Seed rows with `schemaVersion: "1.1.0"` in tags for realism |

---

## Dependencies

Add `pandas>=2.0.0` to `services/api/pyproject.toml`; `uv sync --extra dev`.

---

## Module layout

```
app/domains/telemetry/
  schemas.py, models.py, router.py   # Phases 2–3
  repository.py                    # NEW
  analysis.py                      # NEW — 4 metric functions
  cache.py                         # NEW
```

---

## Step 1 — Repository (`repository.py`)

Unchanged from prior plan — `load_events(session, event_types, start, end)` returns DataFrame with `id`, `timestamp`, `event_type`, `tags`.

Filter `event_type` + `timestamp` in SQL only.

---

## Step 2 — Analysis functions (`analysis.py`)

Each docstring must reference:

1. KPI from [`telemetry-plan.md`](../../../../docs/telemetry/telemetry-plan.md) §2
2. CONTEXT metric replaced (per design § Reconciliation with CONTEXT)

### 2.1 `consumption_volume_per_day` → KPI 1

- **Event:** `supply_consumption_created` only
- **Replaces CONTEXT:** `dispensing_volume_per_day`
- Group: `['date', 'clinic_id', 'jurisdiction']`

### 2.2 `waste_rate_per_day` → KPI 2

- **Event:** `supply_consumption_created`
- **Replaces CONTEXT:** `emergency_dispensing_per_day`
- `consumption_type` from `tags`; `is_waste = expiry_waste`

### 2.3 `insufficient_stock_failures_per_day` → KPI 3

- **Event:** `supply_consumption_failed` only (not `supply_consumption_form_abandoned`)
- **Replaces CONTEXT:** stock-out observability via rejection signal
- Group: `['date', 'jurisdiction']`

### 2.4 `auth_failure_rate`

- **Events:** `user_login_succeeded`, `user_login_failed`
- Group: `['date', 'jurisdiction']`; drop rows without jurisdiction

### Function rules

- Pure; SQL filter first; Pandas aggregations only; no row loops
- Return `[]` for empty windows

---

## Step 3 — Cache (`cache.py`)

60s TTL; key = normalised `(start_iso, end_iso)` UTC.

---

## Step 4 — Report endpoint

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

`GET /telemetry/report` with `Depends(get_current_user)` on route only; `POST /events` stays public.

Default window: 7 days; inclusive start, exclusive end.

---

## Step 5 — Tests (`tests/test_telemetry_report.py`)

Seed fixture should include:

- Standard KPI events with `schemaVersion: "1.1.0"` in tags
- Optional v1.1 rows (`supply_consumption_form_abandoned`, `incident_list_filter_applied`) — assert they **do not** affect KPI metric counts

| Case | Assert |
|------|--------|
| KPI 3 count | Only `supply_consumption_failed` rows counted, not abandon events |
| v1.1 rows in DB | Report still returns 4 metric keys only |
| 401 without token | yes |
| Cache hit within 60s | yes |

---

## Verification

### Seed data (≥20 rows)

Backoffice flows per Phase 2 + storage plan, **including**:

- Abandon outbound form
- Change incident filter

### Authenticated curl

```bash
curl -s "http://localhost:8000/api/v1/telemetry/report" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

Confirm 4 metric arrays; v1.1 events visible in DB but not in response.

---

## PR checklist

- **Title:** `[W17D49] Telemetry Report`
- **Description:** 4 metrics → business questions; note v1.1 events stored but not in report scope

---

## Definition of done

- [ ] 3 KPI metrics + `auth_failure_rate` implemented
- [ ] Docstrings reference `telemetry-plan.md` KPIs + CONTEXT replacements
- [ ] KPI 3 uses `supply_consumption_failed` only (not abandon)
- [ ] JWT on report; ingest unchanged
- [ ] 60s cache; pytest passing
- [ ] v1.1 stored events do not alter report response shape

---

## Full milestone completion

| Phase | Deliverable |
|-------|-------------|
| 1 | `telemetry-plan.md` v1.1.0, `event-schemas.json` (11 events) |
| 2 | TelemetryService + 10 instrumentable events |
| 3 | `telemetry_events` persistence (incl. v1.1) |
| 4 | Report API — 4 metrics over KPI event types |

**Future extension (not Phase 4):** optional `form_abandon_per_day` or `incident_filter_activity_per_day` metrics from v1.1 events.
