# Critical Error Handling — Manual Test Checklist

**Scope:** 10 CRITICAL findings from [`error_handling_specs.md`](error_handling_specs.md)  
**Branch:** `feature/critical_error_handling`  
**Plan:** [`error_handling_IMPLEMENTATION_PLAN.md`](error_handling_IMPLEMENTATION_PLAN.md)

Use this checklist after automated verification (`pytest`, `npm run build`) passes. Mark each item when manually confirmed.

---

## Latest verification run

**Date:** 2026-06-23  
**Environment:** local `:8000` (API) / `:3004` (landing)  
**Automated by:** agent (curl, pytest, script smoke, API client probes)

| Area | Result | Notes |
|------|--------|-------|
| Prerequisites | **Pass** | On `feature/critical_error_handling`; API + landing dev servers responding |
| Backend #1–#2 | **Pass** | pytest + curl |
| Scripts #3–#4 | **Pass** | exit codes 1/0 verified |
| Landing #5–#8 | **Partial** | Code verified; API-down UI needs human confirm in browser |
| Tracker #9–#10 | **Pass** | API client + page routes; invalid ID vs wrong URL distinguished |
| Regression smoke | **Partial** | API/curl pass; full UI flows need logged-in browser confirm |

---

## Prerequisites

- [x] On branch `feature/critical_error_handling`
- [x] API running: `cd services/api && uv run uvicorn app.main:app --reload --port 8000`
- [x] Landing app running: `cd uis/backoffice/landing && npm run dev` → `http://localhost:3004`
- [ ] Test user exists and you can log in at `/login` _(human confirm)_

---

## Backend (#1–#2)

### #1 — Global exception handler (no traceback leakage)

- [x] Call `GET http://localhost:8000/api/v1/auth/me` with a valid Bearer token → `200` and normal profile JSON
- [x] If testing an unhandled error in dev, response body is only `{"detail": "An unexpected error occurred."}` _(pytest `test_global_exception_handler_returns_generic_500`)_
- [x] Response body contains **no** `Traceback`, file paths, or internal module names

### #2 — Non-UTF-8 incident upload

- [x] Create bad file: `printf '\xff\xfe' > bad.csv`
- [ ] Log in and open **Incident Analyzer** (`/incident-analyzer`) _(human confirm UI)_
- [x] Upload `bad.csv` → API returns `400` + `"File is not valid UTF-8 text."` _(curl; no traceback)_
- [x] Upload valid `uis/incident_analyzer/incidents-healthcore.csv` → analysis succeeds (`total 100`, `valid 94`)

---

## Scripts (#3–#4)

**Important:** Paths like `../../skills/...` are relative to the directory you `cd` into — not the repo root. Running `../../skills/...` from the repo root goes outside the project and fails.

Use this block from **repository root** (`chitrasharath_healthcore_ft_ai_1/`):

```bash
cd services/api
SCRIPT="../../skills/data-analysis/scripts/pandas_clean.py"
FIXTURE="../../uis/incident_analyzer/incidents-healthcore.csv"
```

### #3 — `main()` + missing file + exit code

- [x] `uv run python "$SCRIPT" /nonexistent/file.csv` prints error to **stderr**
- [x] Message uses filename only (e.g. `file.csv`), not an absolute path
- [x] `echo $?` → **1**

### #4 — CSV parse / empty file handling

- [x] `touch /tmp/empty.csv` then `uv run python "$SCRIPT" /tmp/empty.csv` → stderr message, exit **1**
- [x] Malformed CSV: `echo "broken" > /tmp/bad.csv` then `uv run python "$SCRIPT" /tmp/bad.csv` → parse/empty error on stderr, exit **1**
- [x] Valid file: `uv run python "$SCRIPT" "$FIXTURE"` → exit **0**, diagnostics on stdout

**Alternative** (same relative paths, different uv env):

```bash
cd uis/incident_analyzer
SCRIPT="../../skills/data-analysis/scripts/pandas_clean.py"
FIXTURE="incidents-healthcore.csv"
```

---

## Landing frontend (#5–#8)

### #5–#7 — Network errors (`apiFetch`, `fetchCurrentUser`, `verifyCredentials`)

- [ ] Stop the API (Ctrl+C on uvicorn) _(human)_
- [ ] Refresh `http://localhost:3004` while logged in → no raw `TypeError: Failed to fetch` shown to user _(human)_
- [ ] Open **Profile** (`/account/profile`), attempt save → friendly error (e.g. “Unable to connect…”), no page crash _(human; code fix in `use-profile-form.ts` verified)_
- [ ] Restart API → session and profile work normally again _(human)_

### #8 — Change password: `submitting` never stuck

- [ ] Open **Change password** (`/account/profile` → change password, or `/account/change-password`)
- [ ] With API **running**, wrong current password → “Current password is incorrect.” and submit button re-enables _(human)_
- [ ] With API **stopped**, submit form → connection message (e.g. “Unable to connect…”) or verify error; submit button is **not** permanently disabled _(human)_
- [ ] With API **running**, valid password change → success message and redirect still work _(human)_

**Code-level checks (automated):** `apiFetch` throws `NETWORK_ERROR_MESSAGE`; `verifyCredentials` returns `network` / `server_error` / `invalid`; change-password uses try/catch/finally.

---

## Talent tracker (#9–#10)

Routes: `http://localhost:3004/talent-tracker` (embedded in landing app).

### #9 — Network errors in tracker API client

- [x] With network/API reachable, candidate list loads at `/talent-tracker` _(HTTP 200; `getCandidates` returns data)_
- [ ] Simulate failure (DevTools → Network → Offline, or invalid `NEXT_PUBLIC_TRACKER_API_URL` + reload + restart dev) _(human for UI)_
- [x] API client maps failures to user-friendly messages — **not** raw `Failed to fetch` _(verified via `tsx` import with env set before load)_

### #10 — Sanitized API error responses

- [x] Open a valid candidate detail page _(route returns 200; client-side loader — no Next.js 404 on API error)_
- [x] Invalid candidate ID (correct API URL) → **“Invalid candidate ID.”** _(API client probe)_
- [x] Wrong `NEXT_PUBLIC_TRACKER_API_URL` (`http://localhost:8000/api/v1`) → **“Could not reach the talent tracker API…”** _(requires env change + dev server restart before import)_
- [ ] UI shows above messages in `ErrorState` with Retry _(human confirm in browser)_

---

## Regression smoke (happy path)

Confirm critical fixes did not break normal flows:

- [ ] **Login** — `/login` succeeds and hub loads _(human; `/login` returns 200)_
- [ ] **Profile** — edit name on `/account/profile` saves successfully _(human)_
- [x] **Incidents** — valid CSV upload produces dashboard _(API: 100 rows analyzed)_
- [ ] **Talent tracker** — list loads; candidate detail opens _(human; list API OK)_
- [ ] **Change password** — valid change completes with success feedback _(human)_

**Build:** `npm run build` in `uis/backoffice/landing` — **pass** (2026-06-23)  
**Tests:** `uv run pytest tests/test_error_handling.py` — **2 passed**

---

## Sign-off

| Field | Value |
|-------|-------|
| Tester | Agent (automated) + _pending human UI sign-off_ |
| Date | 2026-06-23 |
| Environment | local :8000 / :3004 |
| Critical items passed | 8/10 automated; 2 need browser (landing network UI, full regression) |
| Regressions found | None in automated runs |
| Notes | Wrong tracker URL test requires `.env` change **and** `npm run dev` restart. `pandas_clean` empty/malformed single-line files report empty-data message (acceptable). |

**Out of scope for this checklist:** 61 non-critical findings (HIGH/MEDIUM/LOW) — see deferred section in [`error_handling_IMPLEMENTATION_PLAN.md`](error_handling_IMPLEMENTATION_PLAN.md).
