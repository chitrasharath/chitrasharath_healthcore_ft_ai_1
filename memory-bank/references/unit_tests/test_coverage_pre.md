# Workspace Test Coverage Report

**Generated:** 2025-06-24  
**Repository:** `chitrasharath_healthcore_ft_ai_1`

This report summarizes automated test coverage across the HealthCore monorepo. Coverage was measured by running existing test suites and inspecting how each package is verified today.

---

## Executive Summary

| Area | Automated tests | Measurable line coverage | Status |
|------|-----------------|--------------------------|--------|
| `services/api` (FastAPI backend) | **70 pytest tests** | **94.1%** (763 / 811 statements) | Strong |
| `apps/src` (Milestone 2 business logic) | **45 assertions** in custom runner | Not instrumented (function-level only) | Good for utils |
| `uis/*` (Next.js apps) | None | **0%** | Lint + build only |
| `apps/talent-pipeline-tracker` | API smoke script only | **0%** | Integration smoke, not unit tests |
| `uis/incident_analyzer` (Python CLI) | None | **0%** | No tests |
| `packages/shared` | None | **0%** | Types only |
| `apps/healthcore_web_portal` (legacy) | None | **0%** | Static HTML/JS |
| `agents/_template` | Skeleton docs only | **0%** | Placeholder |

**Bottom line:** The only package with instrumented line coverage is **`services/api` at 94.1%**. The rest of the workspace relies on build/lint verification, manual UI testing, or a small custom test runner for Milestone 2 utilities. There is **no workspace-wide coverage tool** (no Jest/Vitest/c8, no unified CI coverage gate).

Approximate scope:

- **~306** source files (`.ts`, `.tsx`, `.py`, `.js`) across the repo
- **~6** dedicated test entry points (`services/api/tests/*`, `apps/src/tests/run-tests.ts`, 2× API smoke scripts)
- **~2%** of source files have a corresponding automated test file

---

## How Coverage Was Measured

### Backend API (`services/api`)

```bash
cd services/api
uv sync --extra dev
uv run pip install pytest-cov
uv run pytest --cov=app --cov-report=term-missing
```

**Result:** 70 tests passed in ~23s.

| Metric | Value |
|--------|-------|
| Total statements | 811 |
| Covered statements | 763 |
| Missed statements | 48 |
| **Line coverage** | **94.1%** |

#### Test breakdown by module

| Test file | Tests | Focus |
|-----------|-------|-------|
| `tests/test_auth.py` | 37 | Register, login, JWT, users CRUD, password reset |
| `tests/test_suppliers.py` | 29 | Supplier CRUD, validation, filters, auth guards |
| `tests/test_incidents.py` | 4 | CSV analyze, export, auth guards |

#### Files below 100% coverage

| Coverage | Statements | File |
|----------|------------|------|
| 0.0% | 3 | `app/__main__.py` |
| 84.4% | 32 | `app/domains/reporting/incidents/router.py` |
| 84.6% | 39 | `app/domains/users/router.py` |
| 86.4% | 22 | `app/seed.py` |
| 87.5% | 48 | `app/domains/procurement/suppliers/router.py` |
| 90.0% | 10 | `app/main.py` |
| 91.2% | 34 | `app/domains/auth/reset_service.py` |
| 92.0% | 50 | `app/domains/users/service.py` |
| 92.3% | 26 | `app/domains/reporting/incidents/service.py` |
| 93.2% | 118 | `app/domains/procurement/suppliers/schemas.py` |
| 94.3% | 53 | `app/domains/procurement/suppliers/service.py` |
| 94.7% | 38 | `app/domains/auth/token.py` |
| 97.8% | 46 | `app/domains/users/store.py` |
| 98.3% | 58 | `app/domains/auth/schemas.py` |

Most gaps are in CLI entry points (`__main__.py`, `seed.py`), error/edge paths in routers, and a few validation branches in schemas.

---

### Milestone 2 utilities (`apps/src`)

```bash
npx -y tsx apps/src/tests/run-tests.ts
```

**Result:** All lightweight tests passed.

| Module | Exported functions | Covered by tests |
|--------|-------------------|------------------|
| `utils/collections.ts` | 5 | Yes |
| `utils/search.ts` | 3 | Yes |
| `utils/transformations.ts` | 11 | Yes |
| `utils/validations.ts` | 4 | Yes |
| **Total** | **22 / 22** | **100% function coverage** |

The runner uses **45 assertions** across collections, search, transformations, validations, and edge cases (empty arrays, invalid dates, zero fees).

**Not covered by automated tests:**

- `main.ts` — CLI/demo harness (~850 lines)
- `types/models.ts` — type definitions only
- `index.html` — manual browser test page

There is no Istanbul/c8/Vitest configuration, so **line/branch coverage is not measured** for TypeScript.

---

### Frontend apps (`uis/*`)

Seven Next.js apps exist. Each exposes `npm run verify` as **lint + build** (and API smoke for talent-tracker variants). None define unit or component tests.

| Package | Source files (approx.) | Test tooling |
|---------|------------------------|--------------|
| `uis/website` | — | Lint + build |
| `uis/backoffice/backoffice_functions` | — | Lint + build (+ manual test dashboard UI) |
| `uis/backoffice/talent-tracker` | — | Lint + build + API smoke |
| `uis/backoffice/landing` | — | Lint + build |
| `uis/supplier_directory` | — | Lint + build |
| `uis/incident_analyzer` | — | Lint + build |
| **Total `uis/`** | **~206** `.ts`/`.tsx`/`.py` files | **0% automated test coverage** |

The backoffice manual test dashboard (`uis/backoffice/backoffice_functions`) exercises Milestone 2 logic interactively but is **not** an automated regression suite.

---

### Talent Pipeline Tracker (`apps/talent-pipeline-tracker`)

| Check | Type | Coverage impact |
|-------|------|-----------------|
| `npm run lint` | Static analysis | None |
| `npm run build` | Compile check | None |
| `npm run api:smoke` | Live HTTP checks against external Talent Tracker API | Connectivity only; does not measure app code coverage |

~47 TypeScript/TSX source files; **0% unit/component test coverage**.

---

### Incident Analyzer Python (`uis/incident_analyzer`)

`analysis_core.py` and `analyze.py` contain CSV loading, validation, and analysis logic (~300+ lines). **No pytest or other tests exist** in this package. Related API behavior is partially tested via `services/api/tests/test_incidents.py` (4 tests against the FastAPI incidents domain, not this CLI module directly).

---

### Shared packages & legacy

| Path | Notes |
|------|-------|
| `packages/shared` | Single types file; no tests |
| `apps/healthcore_web_portal` | Legacy static site (`validation.js`); no tests |
| `agents/_template/tests` | Documentation skeleton only |

---

## Workspace Coverage Estimate

Because only `services/api` uses a coverage tool, a single “whole repo” percentage is not directly available. Reasonable interpretations:

| View | Estimate |
|------|----------|
| **Instrumented line coverage (API only)** | **94.1%** of `services/api/app` |
| **M2 business-logic functions** | **100%** of exported utility functions (22/22), uninstrumented |
| **All other code** | **0%** measured automated coverage |
| **Rough blended line coverage** (811 API stmts + ~2,500+ est. frontend/CLI lines untested) | **~20–25%** if treating the whole monorepo as one codebase — dominated by untested UI and CLI code |

The blended figure is indicative only; the repo was not built as a single coverage project.

---

## Verification Commands (quick reference)

| Package | Command |
|---------|---------|
| API tests + coverage | `cd services/api && uv run pytest --cov=app --cov-report=term-missing` |
| M2 unit tests | `npx -y tsx apps/src/tests/run-tests.ts` |
| Website | `cd uis/website && npm run verify` |
| Backoffice functions | `cd uis/backoffice/backoffice_functions && npm run verify` |
| Talent tracker (uis) | `cd uis/backoffice/talent-tracker && npm run verify` |
| Talent pipeline tracker | `cd apps/talent-pipeline-tracker && npm run verify` |

---

## Gaps and Recommendations

1. **Add Vitest (or similar) to Next.js apps** — Start with pure `lib/` helpers (validation, API clients, hooks) in `uis/website` and `uis/incident_analyzer`.
2. **Instrument M2 TypeScript** — Wire `c8` or Vitest coverage around `apps/src/tests/run-tests.ts` for line/branch metrics.
3. **Test `uis/incident_analyzer/analysis_core.py`** — Port or share fixtures with `services/api/tests/test_incidents.py` to avoid duplicated untested analysis logic.
4. **Close API gaps** — Target routers and `app/__main__.py` / `seed.py` to push API coverage toward 98%+.
5. **CI coverage gate** — Publish `pytest-cov` (and future frontend coverage) in CI with a minimum threshold for `services/api`.

---

## Artifacts Produced During This Report

Running API coverage generated `services/api/coverage.json` locally. That file is useful for tooling but is not part of the standard repo layout; add it to `.gitignore` if you plan to run coverage regularly.
