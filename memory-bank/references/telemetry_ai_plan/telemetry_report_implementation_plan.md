---
name: Telemetry Report (Phase 4)
overview: "Pandas analysis pipeline + JWT-protected GET /api/v1/telemetry/report with three reconciled KPI metrics, optional auth_failure_rate, and 60s in-memory cache."
todos:
  - id: step0-prereq
    content: Confirm Phase 3 persistence live; seed ≥20 telemetry_events via backoffice activity on feature/telemetry
    status: pending
  - id: step1-pandas-dep
    content: Add pandas to services/api/pyproject.toml; uv sync + re-lock root dev group if needed
    status: pending
  - id: step2-repository
    content: Add telemetry/repository.py — parameterised SQL load by event_type + timestamp window
    status: pending
  - id: step3-analysis
    content: Implement analysis.py metric functions (3 required + auth_failure_rate)
    status: pending
  - id: step4-cache
    content: Add telemetry/cache.py — 60s TTL keyed by normalised date window
    status: pending
  - id: step5-report-endpoint
    content: GET /telemetry/report with date params; wire router with get_current_user protection
    status: pending
  - id: step6-tests
    content: Add tests/test_telemetry_report.py — metric shapes, empty window, cache hit, auth 401
    status: pending
  - id: step7-verify
    content: curl authenticated report JSON; confirm KPI traceability docstrings; update memory-bank
    status: pending
isProject: false
---

# Telemetry — Phase 4 (Report) Implementation Plan

**Plan file:** [`memory-bank/references/telemetry_ai_plan/telemetry_report_implementation_plan.md`](telemetry_report_implementation_plan.md)

**Requirements source:** [`telemetry_report_specs.md`](telemetry_report_specs.md), KPI definitions from Phase 1 `telemetry-plan.md`

**Branch:** `feature/telemetry` (fourth commit on same branch)

**Working directory:** `services/api/`

**Status:** Not started — no `pandas` dependency, no report endpoint

---

## Executive summary

Phase 4 turns persisted `telemetry_events` rows into **actionable operational metrics** answering the three reconciled KPIs from Phase 1. Pure Pandas functions in `analysis.py` load data via parameterised SQL (filter `event_type` + `timestamp` in the database, never in Pandas), aggregate by date/clinic/jurisdiction, and return JSON-serialisable `list[dict]` results.

`GET /api/v1/telemetry/report` resolves the date window, applies a **60-second in-memory cache**, and returns `{ period, metrics }`. The endpoint is **JWT-protected** (stakeholder locked — unlike the public ingest endpoint).

---

## Planning decisions (locked)

| Topic | Decision |
|-------|----------|
| Data source | `telemetry_events` on **`milestone5_inventory`** (`DATABASE_URL`) |
| `pandas` | Add to `services/api/pyproject.toml` only (not root unless dev group alignment required) |
| Pipeline order | `load(SQL) → refine(Pandas) → convert types → group → aggregate → to_dict` |
| Date bounds | Inclusive start, exclusive end; endpoint owns defaults (7-day window) |
| US/UK segmentation | Never combined — always group by `jurisdiction` where applicable |
| Auth on report | **Protected** — `Depends(get_current_user)` on report route |
| Auth on ingest | Remains **public** (Phase 2/3) |
| Cache | In-memory dict, 60s TTL, key = normalised `(start_date, end_date)` ISO strings |
| `auth_failure_rate` | **Include** — Phase 2 instruments auth events |
| Tests | pytest with seeded SQLite rows + auth header |
| Branch | Final commit on `feature/telemetry` |

---

## Dependencies

### `services/api/pyproject.toml`

```toml
dependencies = [
    ...
    "pandas>=2.0.0",
]
```

```bash
cd services/api && uv sync --extra dev && uv lock
# Re-lock root uv.lock if project convention requires dual lockfiles
```

---

## Module layout

```
app/domains/telemetry/
  schemas.py      # unchanged from Phase 2
  models.py       # Phase 3
  router.py       # ingest + report routes
  repository.py   # NEW — SQL loaders
  analysis.py     # NEW — pure metric functions
  cache.py        # NEW — TTL cache helper
```

---

## Step 1 — Repository (`repository.py`)

```python
def load_events(
    session: Session,
    event_types: list[str],
    start: datetime,
    end: datetime,
) -> pd.DataFrame:
    """Return columns: id, timestamp, event_type, tags (dict)."""
```

Use `sqlalchemy.text` with bound parameters:

```sql
SELECT id, timestamp, event_type, tags
FROM telemetry_events
WHERE event_type = ANY(:event_types)
  AND timestamp >= :start
  AND timestamp < :end
```

**Rules:**

- Filter `event_type` and `timestamp` in SQL only
- Return empty DataFrame (not error) when no rows
- Parse `tags` as dict (JSONB → Python)

---

## Step 2 — Analysis functions (`analysis.py`)

Each function signature:

```python
def consumption_volume_per_day(
    session: Session,
    start_date: datetime,
    end_date: datetime,
) -> list[dict]:
```

**Docstring requirement (eval criterion 9):** Each function must state:

1. Which Phase 1 KPI it answers
2. Which CONTEXT metric it replaces

### 2.1 `consumption_volume_per_day` → KPI 1

- **Replaces CONTEXT:** `dispensing_volume_per_day`
- SQL: `event_type = 'supply_consumption_created'`
- Refine: extract `clinic_id`, `jurisdiction` from `tags`; drop nulls
- `pd.to_datetime(df['timestamp'], utc=True)` → `df['date'] = df['timestamp'].dt.date`
- `groupby(['date','clinic_id','jurisdiction'])['id'].count()` → rename `count`
- Return rows: `{ date, clinic_id, jurisdiction, count }` (date as ISO string in JSON)

### 2.2 `waste_rate_per_day` → KPI 2

- **Replaces CONTEXT:** `emergency_dispensing_per_day` (no emergency data in codebase)
- SQL: `event_type = 'supply_consumption_created'`
- Refine: `jurisdiction`, `consumption_type` from `tags`; `is_waste = consumption_type == 'expiry_waste'`
- Group `['date','jurisdiction']`:

```python
agg = df.groupby(['date','jurisdiction']).agg(
    total=('id', 'count'),
    waste=('is_waste', 'sum'),
)
agg['waste_rate'] = agg['waste'] / agg['total']
```

- Return: `{ date, jurisdiction, waste_rate, total }` — `waste_rate` float in `[0.0, 1.0]`

### 2.3 `insufficient_stock_failures_per_day` → KPI 3

- **Replaces CONTEXT:** stock-out observability (rejection signal vs stored zero stock)
- SQL: `event_type = 'supply_consumption_failed'`
- Refine: `jurisdiction` from `tags`; drop null jurisdiction
- Group `['date','jurisdiction']` count
- Return: `{ date, jurisdiction, count }`

### 2.4 `auth_failure_rate` (optional but included)

- SQL: `event_type IN ('user_login_succeeded', 'user_login_failed')`
- Refine: `jurisdiction` from `tags` where present; rows without jurisdiction can be dropped or grouped under `unknown` — **prefer drop for CCO segmentation purity**
- Per `['date','jurisdiction']`:

```python
failure_rate = failed / (failed + succeeded)
```

- Return: `{ date, jurisdiction, failure_rate }`

### Function rules (all)

- Pure — no writes; accept explicit `start_date`/`end_date` from caller
- No `for` loops over DataFrame rows for metric computation
- Return `[]` for empty periods
- JSON-serialisable: convert `date` to `str`, numpy scalars to Python floats/ints

---

## Step 3 — Cache (`cache.py`)

```python
@dataclass
class CacheEntry:
    payload: dict
    expires_at: float

_cache: dict[tuple[str, str], CacheEntry] = {}
TTL_SECONDS = 60

def get_cached_report(key: tuple[str, str]) -> dict | None: ...
def set_cached_report(key: tuple[str, str], payload: dict) -> None: ...
```

Key: `(start_iso, end_iso)` normalised to UTC ISO strings.

---

## Step 4 — Report endpoint

### `router.py` addition

```python
@router.get("/report")
def telemetry_report(
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    session: Session = Depends(get_supabase_db),
    _: dict = Depends(get_current_user),
) -> dict:
```

**Window resolution:**

```python
end = end_date or datetime.now(timezone.utc)
start = start_date or (end - timedelta(days=7))
# inclusive start, exclusive end: pass start, end to metrics as-is
```

**Response shape:**

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

### Router registration

Report route lives on the same `telemetry_router`. Protection options:

**Option A (recommended):** Apply `Depends(get_current_user)` on the `/report` route only; leave `POST /events` public.

```python
@router.get("/report", dependencies=[Depends(get_current_user)])
```

**Option B:** Split routers — not needed if per-route dependency works.

Ingest `POST /events` remains without auth.

---

## Step 5 — Tests (`tests/test_telemetry_report.py`)

Seed `telemetry_events` rows in SQLite fixture with varied `event_type` and `tags`:

| Case | Assert |
|------|--------|
| `GET /telemetry/report` without token | 401 |
| With auth + seed data | 200, `metrics` keys present |
| `consumption_volume_per_day` | Correct count for clinic/date |
| `waste_rate_per_day` | Rate 0.5 when 1 waste / 2 total same day+jurisdiction |
| Empty window | All metric arrays `[]` |
| Cache | Second identical request within 60s does not change result; mock/spy repository call count |
| Date params | Custom `start_date`/`end_date` respected in `period` |

---

## Verification

### 1. Seed data

Run backoffice flows until ≥20 `telemetry_events` rows exist (or insert fixture rows in test DB).

### 2. Authenticated curl

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"...","password":"..."}' | jq -r .access_token)

curl -s "http://localhost:8000/api/v1/telemetry/report" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

### 3. Cache smoke

Two requests within 60s — same payload; optional log assertion that SQL load runs once.

### 4. Docstring audit

```bash
rg "KPI|CONTEXT|replaces" services/api/app/domains/telemetry/analysis.py
```

---

## Documentation updates (post-verify)

Update `memory-bank/progress.md` and `memory-bank/decisions.md`:

- Telemetry milestone delivered (4 phases)
- Decision: public ingest vs protected report
- Decision: pandas added to API dependencies
- Decision: KPI reconciliation documented in `docs/telemetry/telemetry-plan.md`

---

## PR checklist

- **Title:** `[W17D49] Telemetry Report`
- **Description:** metric → business question mapping, sample JSON, `auth_failure_rate` included, report endpoint JWT-protected

---

## Definition of done (maps to spec §7)

- [ ] `analysis.py` with ≥3 independent pure metric functions + auth_failure_rate
- [ ] Pipeline: SQL filter → Pandas refine/aggregate; no row loops
- [ ] `pd.to_datetime(..., utc=True)` before temporal groupby
- [ ] JSON-serialisable `list[dict]` per metric with grouping dimension
- [ ] `GET /api/v1/telemetry/report` with 7-day default, `{ period, metrics }`
- [ ] 60s TTL cache
- [ ] Metrics map to Phase 1 reconciled KPIs; docstrings name CONTEXT replacements
- [ ] JWT required on report; ingest unchanged
- [ ] pytest passing

---

## Full milestone completion

After Phase 4 merge, `feature/telemetry` delivers:

| Phase | Deliverable |
|-------|-------------|
| 1 | `docs/telemetry/telemetry-plan.md`, `event-schemas.json` |
| 2 | `TelemetryService`, stub ingest, instrumentation |
| 3 | `telemetry_events` persistence |
| 4 | Report API + Pandas metrics |

Single PR or stacked PRs from `feature/telemetry` → `main` per team preference.
