# specs.md — Error Handling: Backoffice Frontend + FastAPI Backend

## Overview

Audit and harden error handling across the **backoffice frontend apps** and the **FastAPI backend**. The goal is a consistent, user-friendly error experience: no silent failures, no raw technical messages, no undefined UI states, and no sensitive data leaking to clients.

**This is not a feature build.** Do not add new routes, pages, or business logic. Only improve the resilience and error communication of existing code.

---

## Scope

### In scope

| Layer | Location |
|-------|----------|
| Frontend — Backoffice Landing | `uis/backoffice/landing/` |
| Frontend — Backoffice Functions | `uis/backoffice/backoffice_functions/` |
| Frontend — Talent Tracker | `uis/backoffice/talent-tracker/` |
| Shared API client | `uis/backoffice/shared/lib/healthcore-api.ts` |
| Backend — FastAPI | `services/api/` |
| Script — Incident Analyzer CLI | `uis/incident_analyzer/analyze.py` + `uis/incident_analyzer/analysis_core.py` |
| Script — Pandas Clean | `skills/data-analysis/scripts/pandas_clean.py` |

### Out of scope

- `uis/website/`, `uis/supplier_directory/`, `uis/incident_analyzer/` (frontend apps — only the CLI script is in scope)
- `apps/` directory (older apps)
- New features, refactors, or abstractions unrelated to error handling

---

## Frontend Patterns

Apply these rules to every component, hook, and page in the three backoffice apps.

### FE-1: Three-state UI for every async operation

Every hook or component that fetches data must track and render three states:

1. **Loading** — show a spinner, skeleton, or "Loading…" text while the request is in flight.
2. **Success** — render the data normally.
3. **Error** — show a human-readable message with a call to action (see FE-3).

Scan every `useEffect` that calls `fetch`, `apiFetch`, or `healthcoreFetch`, and every form-submit handler. Confirm each one sets a `loading` flag before the request and clears it in a `finally` block, and handles the error path with a user-visible message.

### FE-2: `finally` blocks for loading state cleanup

Every async operation that sets `loading = true` (or `submitting = true`) must clear it inside a `finally` block — never only in the success path or only in the catch path. This prevents the UI from getting stuck in a loading state.

Pattern:
```ts
setLoading(true);
try {
  // await …
} catch {
  // set error message
} finally {
  setLoading(false);
}
```

### FE-3: Human-readable error messages with a call to action

No user-facing error message should contain:
- Raw status codes (`Error 500`, `404`)
- Exception names (`TypeError`, `SyntaxError`)
- JSON parsing artifacts (`Unexpected token <`)
- Stack traces or internal paths

Every error state must offer at least one of:
- A **retry button** that re-triggers the failed operation
- A **navigation link** (e.g., "Go back to dashboard")
- A **support/contact prompt** (e.g., "If this persists, contact support.")

Use the existing `ErrorState` component pattern from `uis/backoffice/talent-tracker/components/states/error-state.tsx` — it already accepts `message` and `onRetry`. Create equivalent components in the other two apps if they don't have one, or extract a shared one.

### FE-4: Optional chaining and safe defaults

When rendering data from API responses, use optional chaining (`?.`) for nested property access and provide fallback values for display:

- `user?.name ?? "Unknown"` instead of `user.name`
- `candidates?.length ?? 0` instead of `candidates.length`
- `item?.status ?? "—"` instead of `item.status`

Audit JSX that renders API data and add guards where a `null` or `undefined` value would cause a crash or render "undefined" literally.

### FE-5: `try/catch` scoped to the dangerous operation

Don't wrap an entire function body in a single try/catch. Scope the try/catch to the specific `fetch`/`await` call that can fail. Code that runs before or after the async call (validation, state updates, navigation) should be outside the catch.

### FE-6: No sensitive data in console output

Remove or guard any `console.log` or `console.error` that dumps full API response bodies, tokens, user data, or error objects that may contain internal paths. In production, error logging should contain only the information needed to debug — not raw payloads.

### FE-7: Network-level fetch failures

The `apiFetch` wrapper in `uis/backoffice/landing/lib/api.ts` and `healthcoreFetch` in `uis/backoffice/shared/lib/healthcore-api.ts` do not currently handle network failures (e.g., `TypeError: Failed to fetch` when the server is down). Callers handle this in their own catch blocks, but the raw `TypeError` message can surface to users.

Ensure that wherever these wrappers are called, the catch block converts network errors into a user-friendly message like "Unable to connect. Please check your connection and try again."

---

## Backend Patterns

Apply these rules to every router, service, and store file in `services/api/`.

### BE-1: Scoped exception handling in route handlers

Each route handler should catch **specific** exceptions at the correct granularity:
- Catch domain exceptions (e.g., `SupplierNotFoundError`, `DuplicateEmailError`) and map them to the correct HTTP status + a clean `detail` message.
- Do **not** catch `Exception` broadly unless it's to prevent leaking internals — and in that case, log the real error server-side and return a generic 500 message.

The existing routers (auth, suppliers, incidents, users) already follow this pattern well. Verify there are no gaps.

### BE-2: Structured error responses

All error responses must use FastAPI's `HTTPException` with a JSON-serializable `detail` field. The response shape should be consistent:

```json
{ "detail": "Human-readable error description" }
```

Never return raw Python tracebacks, internal file paths, database connection strings, or environment variable values in the `detail` field.

### BE-3: No sensitive data in error responses

Audit every `HTTPException` and every place where `str(exc)` is passed as `detail`. Ensure none of these could leak:
- Database file paths (e.g., `db.json` path)
- Internal module paths
- Secret keys, tokens, or credentials
- User passwords or hashed values

If `str(exc)` might contain sensitive info, replace it with a safe, generic message.

### BE-4: Global exception handler

Add a global exception handler to `services/api/app/main.py` that catches any unhandled `Exception` and returns a generic `500` response with `{"detail": "An unexpected error occurred."}`. This prevents FastAPI's default behavior of returning the raw exception message in development mode.

```python
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": "An unexpected error occurred."})
```

### BE-5: Validate external inputs at route boundaries

Ensure that file uploads (`UploadFile`), query parameters, and path parameters are validated before processing. The incidents router already does this for CSV uploads — verify other routes follow the same pattern.

FastAPI's Pydantic validation handles request bodies automatically, but check for any manual parsing (e.g., `await file.read()`, `response.text()`) that could raise unexpected errors.

---

## Script Patterns

Apply these rules to the two Python scripts: `uis/incident_analyzer/analyze.py` and `skills/data-analysis/scripts/pandas_clean.py`.

### SC-1: Wrap file I/O in `try/except` with informative `stderr` messages

Any operation that reads from or writes to the filesystem (`open()`, `pd.read_csv()`, `Path.open()`, `csv.DictWriter`) must be wrapped in a `try/except` that:
- Catches the specific exception (`FileNotFoundError`, `PermissionError`, `pd.errors.EmptyDataError`, `OSError`).
- Prints a clear, actionable message to `stderr` — e.g., `"Error: could not read data.csv — file not found."`.
- Does **not** print the raw traceback to `stdout`.

`analyze.py` already catches `Exception` broadly around the entire `main()` body. Break this into scoped handlers: one for `load_incidents` (file read / CSV parse), one for `write_export_csv` (file write), so the user gets a specific message for each failure mode.

`pandas_clean.py` currently has **no error handling at all** — `pd.read_csv("data.csv")` will crash with an unhandled `FileNotFoundError` if the file is missing, and with a `pd.errors.EmptyDataError` if the file is empty.

### SC-2: Exit with non-zero code on critical errors

When a script encounters a fatal error (missing input file, unparseable CSV, write failure), it must exit with a non-zero exit code.

- `analyze.py` already returns `1` from `main()` on error and uses `raise SystemExit(main())` — this is correct. Verify each new except block also returns `1`.
- `pandas_clean.py` has no `sys.exit()` call at all. Wrap the script body in a `main()` function that returns `0` on success and `1` on failure, and call it via `if __name__ == "__main__": sys.exit(main())`.

### SC-3: Validate inputs before processing

Before doing any heavy processing, check that required inputs exist and are sane:

- **Missing file**: Check `Path.is_file()` before reading. `analyze.py` already does this for the CLI argument — good.
- **Missing CLI arguments**: `analyze.py` already checks `len(sys.argv) != 2` — good.
- **Empty or malformed data**: After loading a CSV/DataFrame, check that it's not empty (`df.empty`) and that expected columns are present before processing. Print a specific error message like `"Error: CSV file is empty or has no valid data."` and exit with code 1.

`pandas_clean.py` does no input validation — it assumes `data.csv` exists and has data.

### SC-4: No sensitive data in script output

Script error messages must not expose:
- Full filesystem paths (use `path.name` instead of the absolute path — `analyze.py` already does this correctly).
- Database connection strings or credentials.
- Raw Python tracebacks to `stdout` (tracebacks to `stderr` are acceptable for developer debugging, but should be behind a `--verbose` flag or simply omitted in favor of the human-readable message).

### SC-5: CSV parsing errors

When parsing CSV data, catch `csv.Error`, `UnicodeDecodeError`, and `pd.errors.ParserError` specifically. Return a message like:
```
Error: could not parse <filename> — the file does not appear to be valid CSV.
```

`analyze.py`'s current broad `except Exception` hides the distinction between "file not found", "not valid CSV", and "analysis logic bug". Splitting these up gives the user actionable information.

---

## Acceptance Criteria

These criteria define "done" for the error handling audit. The coding agent should verify each one after completing implementation.

### Frontend

- [ ] Every hook that fetches data (`useEffect` + fetch) has loading, success, and error states — none are missing.
- [ ] Every error state shown to the user is human-readable (no raw status codes, no exception names, no stack traces).
- [ ] Every error state includes a call to action: retry button, navigation link, or contact prompt.
- [ ] `finally` blocks are used to clear loading/submitting state in every async operation.
- [ ] Optional chaining and fallback values are used wherever API response data is rendered in JSX.
- [ ] No `console.log` or `console.error` leaks sensitive data (tokens, full error objects with internals, user credentials).
- [ ] Network failures (`Failed to fetch`) are caught and shown as user-friendly messages, not raw TypeError text.
- [ ] `npm run build` succeeds for all three backoffice apps without TypeScript errors.

### Backend

- [ ] Every route handler catches domain-specific exceptions and returns the correct HTTP status code with a clean `detail` message.
- [ ] No error response contains Python tracebacks, internal paths, secret keys, or database connection strings.
- [ ] A global exception handler is registered on the FastAPI app that returns `500` with a generic message for unhandled exceptions.
- [ ] `str(exc)` is never passed directly as `detail` if the exception message could contain sensitive information.
- [ ] All existing tests still pass (`pytest`).

### Scripts

- [ ] File I/O operations (`pd.read_csv`, `open`, `Path.open`) are wrapped in `try/except` with specific exception types — not a single broad `except Exception`.
- [ ] Error messages are printed to `stderr`, not `stdout`, and are human-readable (no raw tracebacks).
- [ ] Scripts exit with code `1` on any critical error (missing file, unparseable CSV, write failure).
- [ ] Input validation runs before heavy processing: file existence, non-empty data, expected columns present.
- [ ] Error messages use `path.name` (filename only), never full absolute filesystem paths.
- [ ] `pandas_clean.py` has a `main()` function with `sys.exit()` instead of bare top-level code.

### General

- [ ] No new features, pages, or routes were added — only error handling improvements to existing code.
- [ ] The existing functionality of all three backoffice apps and the API continues to work without regressions.

---

## Audit Report

Full file-by-file audit of every in-scope module. Findings are grouped by severity.

---

### CRITICAL

| # | File | Lines | Pattern | Problem | Suggested Fix |
|---|------|-------|---------|---------|---------------|
| 1 | `services/api/app/main.py` | 1-23 | BE-4 | No global exception handler. Unhandled exceptions produce FastAPI's default 500 with a full Python traceback in debug mode, exposing internal file paths. | Add `@app.exception_handler(Exception)` returning `{"detail": "An unexpected error occurred."}`. |
| 2 | `services/api/app/domains/reporting/incidents/service.py` | 36 | BE-3 | `content.decode("utf-8")` raises `UnicodeDecodeError` with a raw traceback if the uploaded file is not UTF-8. Not caught anywhere. | Wrap in try/except, raise `ValueError("File is not valid UTF-8 text.")`. |
| 3 | `skills/data-analysis/scripts/pandas_clean.py` | 8 | SC-1, SC-2, SC-3 | `pd.read_csv("data.csv")` runs at module top level with zero error handling, no input validation, and no `sys.exit(1)`. Crashes with a full traceback including absolute paths. | Wrap in a `main()` function with try/except for `FileNotFoundError`, `pd.errors.ParserError`, `pd.errors.EmptyDataError`. Call via `sys.exit(main())`. |
| 4 | `skills/data-analysis/scripts/pandas_clean.py` | 8 | SC-5 | CSV parsing errors (`pd.errors.ParserError`, `EmptyDataError`) are not caught. Malformed CSV produces an unhandled traceback. | Catch these specifically in the new `main()`, print a user-friendly message to stderr. |
| 5 | `uis/backoffice/landing/lib/api.ts` | 18 | FE-7 | `apiFetch` calls `fetch()` without catching network errors. `TypeError: Failed to fetch` propagates raw to every caller. | Wrap `fetch()` in try/catch; convert `TypeError` to a user-friendly `NetworkError`. |
| 6 | `uis/backoffice/landing/lib/api.ts` | 53 | FE-7 | `fetchCurrentUser` calls raw `fetch()` (not `apiFetch`) with no network error handling. Raw `TypeError` propagates to `AuthGuard` and `useLandingSession`. | Add try/catch, return `null` on network error. |
| 7 | `uis/backoffice/landing/lib/api.ts` | 76 | FE-7 | `verifyCredentials` calls raw `fetch()` with no try/catch. Network failure throws raw `TypeError` into `useChangePasswordForm`. | Wrap in try/catch, return `"error"` on network failure. |
| 8 | `uis/backoffice/landing/hooks/use-change-password-form.ts` | 70-80 | FE-5, FE-7 | `verifyCredentials` call is outside the try/catch block. Network error = unhandled rejection + `submitting` stuck forever as `true`. | Move `verifyCredentials` inside the try/catch, or add its own try/catch with finally. |
| 9 | `uis/backoffice/talent-tracker/lib/api.ts` | 37, 42 | FE-7 | `requestJson` and `requestVoid` call `fetch()` without catching network errors. `TypeError: Failed to fetch` propagates to every consumer. | Wrap `fetch()` in try/catch, convert to user-friendly message. |
| 10 | `uis/backoffice/talent-tracker/lib/api.ts` | 28-30 | FE-3 | `readResponse` throws raw `response.text()` as the error message. If the API returns HTML, a traceback, or JSON, that raw content is shown to users. | Parse the response, extract a clean message, fall back to a generic string. |

---

### HIGH

| # | File | Lines | Pattern | Problem | Suggested Fix |
|---|------|-------|---------|---------|---------------|
| 11 | `services/api/app/domains/reporting/incidents/router.py` | 24-25 | BE-1 | `except Exception` is overly broad — catches everything including programming errors, masking bugs. | Catch specific exceptions (`pd.errors.ParserError`, `KeyError`, `ValueError`). |
| 12 | `services/api/app/domains/reporting/incidents/router.py` | 23 | BE-2, BE-3 | `detail=str(exc)` on the `ValueError` catch passes the raw exception message to the client. Could leak internal details. | Use a fixed, safe message. |
| 13 | `services/api/app/domains/reporting/incidents/service.py` | 18-23 | BE-3 | `_ensure_analysis_core_importable()` inserts an absolute filesystem path into `sys.path`. If it fails, the traceback exposes server directory structure. | Wrap in try/except, raise a clean error. |
| 14 | `services/api/app/core/db.py` | 16-21 | BE-1 | `TinyDB(DB_PATH)` and `DB_PATH.parent.mkdir()` have no exception handling. Filesystem errors expose full paths. | Wrap in try/except `OSError`, raise a clean `HTTPException` or let the global handler catch it. |
| 15 | `services/api/app/domains/procurement/suppliers/router.py` | 23 | BE-2 | `detail=str(exc)` for `DuplicateSupplierError` — currently benign, but fragile if exception message ever includes internal details. | Use a fixed string: `"A supplier with this name already exists."`. |
| 16 | `uis/incident_analyzer/analyze.py` | 120-121 | SC-1 | Bare `except Exception` swallows all errors and prints a single generic message. Hides whether the problem is file-not-found, bad CSV, or a logic bug. | Split into scoped handlers for `FileNotFoundError`, `pd.errors.ParserError`, `OSError`. |
| 17 | `uis/backoffice/landing/hooks/use-change-password-form.ts` | 67-80 | FE-2 | If `verifyCredentials` throws, `setSubmitting(false)` never runs — submit button stuck permanently disabled. | Restructure so all async work is inside a single try/catch/finally. |
| 18 | `uis/backoffice/landing/hooks/use-profile-form.ts` | 62-64 | FE-3 | Catch block has only a comment (`// 401 redirect handled by apiFetch`) and sets no error state. Non-401 errors silently fail — user sees no feedback. | Add `setError("Could not save profile. Please try again.")` in catch. |
| 19 | `uis/backoffice/landing/components/account/profile-form.tsx` | 20-28 | FE-3 | Error state shows "Could not load profile." with no retry button, no navigation, no way to recover. | Add a "Try again" button or a link to the home page. |
| 20 | `uis/backoffice/landing/hooks/use-change-password-form.ts` | 36-43 | FE-1 | If `/auth/me` returns a non-ok response, no error state is set. `loading` becomes false, `user` is null, and the form renders but does nothing — user is stuck. | Set an error state when user fetch fails; render it in the component. |
| 21 | `uis/backoffice/landing/components/account/change-password-form.tsx` | 9-18 | FE-1 | Component handles `loading` but not a failed load. If user fetch fails, form renders normally but submit silently does nothing. | Expose an `error` state from the hook; render error message with retry/back link. |
| 22 | `uis/backoffice/landing/components/auth/auth-guard.tsx` | 44-49 | FE-3 | If auth check fails and redirect also fails, user is permanently stuck on "Checking authentication…" with no way to proceed. | Add a timeout fallback that shows a link to the login page. |
| 23 | `uis/backoffice/talent-tracker/components/candidate-list-page.tsx` | 28-30 | FE-1 | `handleDelete` catch block is empty (`catch { }`). Deletion failure gives zero user feedback. | Show an error notification or alert when deletion fails. |
| 24 | `uis/backoffice/talent-tracker/components/new-candidate/use-new-candidate-form.ts` | 65-69 | FE-3 | Catch block sets user-facing `message` to raw `submitError.message`, which could be raw API text or "Failed to fetch". | Map to a user-friendly message with a retry call to action. |
| 25 | `uis/backoffice/talent-tracker/components/candidate-edit/use-candidate-notes.ts` | 49, 59 | FE-3 | `addNote` and `removeNote` pass raw `error.message` to `notify("error", ...)`. Messages originate from `readResponse` which can contain raw API response text. | Sanitize before surfacing; use generic user-friendly messages. |
| 26 | `uis/backoffice/talent-tracker/components/candidate-edit/profile-mutations.ts` | 18, 42 | FE-3 | `savePipelineMutation` and `saveCorrectionsMutation` pass raw `error.message` to user-facing `notify`. | Use user-friendly error messages with actionable guidance. |
| 27 | `uis/backoffice/talent-tracker/components/candidate-detail-notes-panel.tsx` | 34, 74 | FE-3 | `loadNotes` and `addNote` set user-facing `message` to raw `error.message`. | Map to user-friendly messages. |
| 28 | `uis/backoffice/talent-tracker/components/candidate-list/use-candidate-list.ts` | 46-48 | FE-3 | Catch passes raw `fetchError.message` to `ErrorState`. Can be raw API text or "Failed to fetch". | Sanitize before surfacing; show generic message with retry. |
| 29 | `uis/backoffice/backoffice_functions/hooks/use-manual-test-runner.ts` | 40-48 | FE-5 | `executeOperation` calls `operation.run(params)` with no try/catch. If any `run()` function throws, the entire React tree crashes. | Wrap `operation.run(params)` in try/catch; store error in result object. |
| 30 | `uis/backoffice/backoffice_functions/hooks/use-manual-test-runner.ts` | 55-59 | FE-5 | `runAll` iterates with `forEach` and no try/catch. One throw skips all remaining operations and crashes the component. | Wrap `executeOperation` inside forEach in try/catch. |
| 31 | `uis/backoffice/backoffice_functions/components/manual-test/result-panel.tsx` | 16 | FE-3 | `formatJson(latestResult.value)` renders whatever `value` contains directly into a `<pre>` block. If errors are stored in `value`, raw technical content is shown. | Check for error indicator; render user-friendly message with retry CTA instead. |

---

### MEDIUM

| # | File | Lines | Pattern | Problem | Suggested Fix |
|---|------|-------|---------|---------|---------------|
| 32 | `services/api/app/domains/reporting/incidents/router.py` | 15-25 | BE-5 | `file.content_type` is not validated. Any file type is accepted; no size limit. | Check content type and/or extension before reading. Consider a size limit. |
| 33 | `services/api/app/domains/reporting/incidents/router.py` | 17 | BE-5 | `if not file.filename` only guards against empty filename, not invalid extension. `report.xlsx` passes but fails during CSV parsing with an unclear error. | Also validate the file extension. |
| 34 | `services/api/app/core/config.py` | 20 | BE-1 | `Settings()` instantiated at import time. Missing env vars cause a `ValidationError` traceback at startup that could expose `.env` paths in logs. | Wrap in a function with a clean startup error message. |
| 35 | `services/api/app/domains/auth/reset_service.py` | 28-36 | BE-1 | `resend.Emails.send()` has no exception handling. If the Resend API is down, the raw exception propagates as an unhandled 500 with internal details. | Wrap in try/except, log the error, return the same privacy-safe response. |
| 36 | `services/api/app/domains/auth/reset_service.py` | 25 | BE-3 | When `email_api_key` is empty, the reset URL (containing the JWT token) is printed to stdout via `print()`. In production, stdout goes to log aggregators — this leaks a security-sensitive token. | Use `logging.debug()` or suppress in non-development environments. |
| 37 | `uis/incident_analyzer/analyze.py` | 87 | SC-1 | `output_path.open("w")` in `write_export_csv` has no try/except. `OSError` on read-only filesystem crashes with a traceback. | Wrap in try/except `OSError`, print user-friendly message to stderr. |
| 38 | `uis/incident_analyzer/analyze.py` | 110-112 | SC-1 | `load_incidents` can raise `pd.errors.ParserError` or `EmptyDataError` for malformed CSVs, but only caught by the broad `except Exception`. User gets a generic message with no indication of the actual problem. | Catch these specifically with targeted messages. |
| 39 | `uis/incident_analyzer/analysis_core.py` | 142 | SC-5 | `pd.read_csv(source, ...)` does not catch parsing errors. Neither the CLI nor the API catches them specifically. | Raise a cleaner domain-specific exception from this library function. |
| 40 | `skills/data-analysis/scripts/pandas_clean.py` | 9-30 | SC-4 | `print()` calls output data that could include column names or values containing PII. Hardcoded path `"data.csv"` prevents specifying input. | Parameterize the input path; consider what data is printed. |
| 41 | `uis/backoffice/landing/components/landing/landing-hero.tsx` | 18 | FE-4 | `{user.name \|\| user.email}` — if API returns `null` for `name`, this renders the literal string "null". | Use `{user.name?.trim() \|\| user.email}`. |
| 42 | `uis/backoffice/landing/components/account/profile-form.tsx` | 70 | FE-4 | `formatAccountDate(user.created_at)` assumes `created_at` is always valid. If null/undefined, shows "Invalid Date" to user. | Add null check: `user.created_at ? formatAccountDate(user.created_at) : "Unknown"`. |
| 43 | `uis/backoffice/landing/hooks/use-landing-session.ts` | 7-47 | FE-1 | Hook exposes no `error` state. UI cannot distinguish "not logged in" from "network error while checking session" — both show the public intro. | Add an `error` state; show a banner in `LandingPage` on failure. |
| 44 | `uis/backoffice/landing/hooks/use-register-form.ts` | 63-80 | FE-5 | try/catch wraps both the API call and error-response JSON parsing. Malformed error response falls to the generic catch, losing the specific API error. | Parse error response JSON in its own try/catch. |
| 45 | `uis/backoffice/landing/hooks/use-register-form.ts` | 24 | FE-4 | `item.loc[item.loc.length - 1]` — if `item.loc` is empty, index is `-1` and the error is silently dropped. | Check `item.loc.length === 0` and map to a form-level error. |
| 46 | `uis/backoffice/talent-tracker/components/candidate-edit/use-candidate-notes.ts` | 30-31 | FE-1 | Notes load failure silently sets `setNotes([])`. User sees an empty list with no error indication or retry option. | Track a notes-specific error state; show error/retry UI. |
| 47 | `uis/backoffice/talent-tracker/components/candidate-edit/use-candidate-notes.ts` | 20 | FE-4 | `setNotes(response.data)` without guarding against undefined. If response shape changes, this crashes. | Use `setNotes(response?.data ?? [])`. |
| 48 | `uis/backoffice/talent-tracker/components/candidate-detail-notes-panel.tsx` | 32, 44 | FE-4 | `response.data` accessed without safe defaults in `loadNotes` and `useEffect`. | Use `response?.data ?? []`. |
| 49 | `uis/backoffice/talent-tracker/components/candidate-detail-notes-panel.tsx` | 65-76 | FE-1 | `addNote` has no loading/submitting state. User can double-click creating duplicates; no visual feedback during async operation. | Add a `submitting` state that disables the button. |
| 50 | `uis/backoffice/talent-tracker/components/candidate-edit/use-candidate-notes.ts` | 41-62 | FE-1 | `addNote` and `removeNote` have no per-operation loading state. Users can trigger multiple simultaneous operations. | Add a `submitting` boolean to prevent double-submissions. |
| 51 | `uis/backoffice/talent-tracker/components/candidate-edit/use-candidate-notes.ts` | 18-21 | FE-7 | `refreshNotes` has no try/catch. Called after mutations — if it fails, unhandled rejection crashes React. | Wrap in try/catch or handle rejection at call sites. |
| 52 | `uis/backoffice/talent-tracker/components/candidate-edit/profile-mutations.ts` | 24-44 | FE-5 | try/catch wraps validation + API call together. Validation error and API error produce the same handling path. | Move validation before the try/catch. |
| 53 | `uis/backoffice/talent-tracker/components/candidate-list/candidate-table.tsx` | 49-50 | FE-4 | `.replace(/_/g, " ")` called directly on `candidate.status` and `candidate.stage`. Null/undefined would throw. | Use optional chaining: `candidate.status?.replace(/_/g, " ") ?? ""`. |
| 54 | `uis/backoffice/shared/lib/healthcore-api.ts` | 18 | FE-7 | `fetch()` not wrapped in try/catch. `TypeError: Failed to fetch` propagates as-is to all consumers. | Wrap in try/catch, convert to user-friendly error. |
| 55 | `uis/backoffice/backoffice_functions/hooks/use-manual-test-runner.ts` | 40-48 | FE-1 | No `isLoading` or `error` state. The hook only tracks `latestResult`. No way to show loading or error states in the UI. | Add `isLoading` and `error` state variables with try/catch/finally. |
| 56 | `uis/backoffice/backoffice_functions/components/manual-test-page.tsx` | 26-28 | FE-3 | "No operations available." fallback has no call to action — no retry, no docs link. | Add a retry/refresh button or helpful guidance message. |
| 57 | `uis/backoffice/backoffice_functions/lib/format-json.ts` | 1 | FE-5 | `JSON.stringify(value, null, 2)` can throw on circular references. Used in `result-panel.tsx` — crash if triggered. | Wrap in try/catch, return `"[Unable to display result]"` on error. |
| 58 | `uis/backoffice/backoffice_functions/lib/operations-registry.ts` | 108-121 | FE-4 | `findLocationById` etc. fall back to `sampleLocations[0]`. If arrays are empty, returns `undefined` causing downstream crashes. | Guard: if array is empty, throw a descriptive error or return a typed default. |
| 59 | `uis/backoffice/backoffice_functions/hooks/use-manual-test-runner.ts` | 15-17 | FE-4 | When `operations` is empty, `selectedOperation` becomes `undefined` via `?? operations[0]` fallback. Hook is in an inconsistent state. | Return an explicit `isEmpty` flag; ensure `selectedOperation` is `OperationDefinition \| null`. |
| 60 | `services/api/app/domains/users/router.py` | 13 | BE-5 | `POST /users` has no authentication guard. Any unauthenticated client can create users — other CRUD endpoints require `get_current_user`. | Add `current_user: dict = Depends(get_current_user)`. |

---

### LOW

| # | File | Lines | Pattern | Problem | Suggested Fix |
|---|------|-------|---------|---------|---------------|
| 61 | `services/api/app/domains/reporting/incidents/service.py` | 19 | BE-3 | `_ensure_analysis_core_importable` hardcodes a relative path traversal (`parents[4].parent.parent`). Brittle; failure exposes directory structure. | Use a more robust path resolution or environment variable. |
| 62 | `services/api/app/domains/users/service.py` | 43, 70 | BE-1 | `assert created is not None` / `assert updated is not None`. Assertions disabled with `python -O` would cause silent `None` propagation. | Use explicit `if`/`raise` instead. |
| 63 | `services/api/app/domains/procurement/suppliers/service.py` | 42, 43 | BE-1 | Same `assert doc is not None` pattern. | Use explicit `if`/`raise`. |
| 64 | `services/api/app/core/dependencies.py` | 12-22 | BE-1 | `get_current_user` calls `store.get_by_id` which could raise unexpected TinyDB exceptions (corrupt JSON). Not caught — raw 500. | Let the global exception handler (finding #1) cover this, or add a targeted catch. |
| 65 | `uis/backoffice/landing/hooks/use-reset-password-form.ts` | 53-54 | FE-3 | Generic "Something went wrong. Please try again." has no specific CTA. The expired-link case has a CTA but the generic case does not. | Add "If this persists, request a new reset link." |
| 66 | `uis/backoffice/landing/app/(protected)/supplier-directory/suppliers/[id]/page.tsx` | 11-17 | FE-3 | "Invalid supplier ID." message has no navigation link to return to the supplier directory. | Add a "Return to supplier directory" link. |
| 67 | `uis/backoffice/talent-tracker/components/candidate-summary-card.tsx` | 39 | FE-4 | `new Date(appliedAt).toLocaleDateString()` — malformed `appliedAt` produces "Invalid Date" shown to user. | Validate the date or provide a fallback like "N/A". |
| 68 | `uis/backoffice/talent-tracker/components/candidate-edit/notes-panel.tsx` | 60 | FE-4 | `new Date(note.created_at).toLocaleString()` — malformed date produces "Invalid Date". | Add date validation or fallback. |
| 69 | `uis/backoffice/talent-tracker/components/candidate-detail-notes-panel.tsx` | 116 | FE-4 | Same `new Date(note.created_at)` issue. | Add date validation or fallback. |
| 70 | `uis/backoffice/talent-tracker/components/candidate-list/use-candidate-list.ts` | 35 | FE-4 | `payload.data` assigned directly to `candidates`. If API response lacks `data`, downstream `.map()` calls crash. | Use `payload?.data ?? []`. |
| 71 | `uis/backoffice/backoffice_functions/components/manual-test/history-panel.tsx` | 14 | FE-4 | Empty history renders `null` — no empty-state message for the user. | Show "No operations run yet." instead of nothing. |

---

### Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 10 |
| HIGH | 21 |
| MEDIUM | 29 |
| LOW | 11 |
| **Total** | **71** |
