# Architectural and Feature Decisions

This document records major decisions across project milestones.

## Decision Log

## Milestone 1

- Decision: Build public website as a static implementation using HTML, JavaScript, and Tailwind CSS.
- Why: Fast delivery for digital credibility and structured patient enquiry intake.

- Decision: Use two-page flow for landing and enquiry form with shared navigation.
- Why: Clear separation of presentation content and form workflow.

- Decision: Include client-side validation and Schema.org markup.
- Why: Improve form quality, accessibility, and search visibility.

## Milestone 2

- Decision: Implement core operational logic as typed TypeScript utility modules.
- Why: Reliability, testability, and reuse across future applications.

- Decision: Separate utility responsibilities by module type.
- Why: Improve maintainability and make business logic easier to verify.

- Decision: Prioritize deterministic, validated calculations for reporting.
- Why: Outputs support weekly operational decisions and must be trusted.

## Milestone 3

- Decision: Build recruiting app with Next.js 16, TypeScript, Tailwind CSS, and App Router.
- Why: Scalable routing, consistent component model, and strong typing.

- Decision: Use custom components and URL-driven filtering/search behavior.
- Why: Control UX behavior and align with technical constraints.

- Decision: Integrate with Talent Tracker API using async/await.
- Why: Keep data flows explicit and resilient across loading and error states.

## Milestone 4 Public Portal Migration

- Decision: Build the migrated public portal at `uis/website` (Next.js 16) while retaining `apps/healthcore_web_portal/` unchanged.
- Why: Enable side-by-side regression comparison and safe cutover per migrate-portal-page-to-next skill.

- Decision: Use route `/enquiry-form` for the patient enquiry page (`app/enquiry-form/page.tsx`).
- Why: Clearer public URL than `/application`; maps from legacy `application.html`.

- Decision: Port enquiry validation into `uis/website` (`lib/enquiry-validation.ts`) without `apps/src` imports in the first delivery.
- Why: M2 utility wiring deferred to a later phase; parity with legacy `validation.js` was the priority.

- Decision: Enforce component constraints (const functional components, ≤80 lines per file) in `uis/website`.
- Why: Align with milestone 3 and agent rules.

- Decision (deferred): Import milestone 2 business logic functions into `uis/website` enquiry workflow.
- Why: Scheduled follow-up per frontend-consume-shared-utilities skill.

## Milestone 2 Backoffice Internal App

- Decision: Build internal manual test UI at `uis/backoffice/backoffice_functions` (Next.js 16) while retaining `apps/src/main.ts`, `apps/src/index.html`, and `apps/src/tests/` unchanged. Parent folder `uis/backoffice/` holds sibling internal apps.
- Why: Modern internal UX without disrupting CLI, automated tests, or legacy browser workflow; parent folder allows future backoffice pages.

- Decision: Copy-only strategy for sample data and operations registry into `uis/backoffice/backoffice_functions/lib/` rather than extracting shared modules from `main.ts`.
- Why: User chose minimal change to `apps/src`; registry duplication documented with cross-reference comments.

### Operations registry implementation (`uis/backoffice/backoffice_functions/lib/operations-registry.ts`)

The registry is a **transcription** of the manual-test wiring in `apps/src/main.ts`, not a reimplementation of business logic.

**What was copied from `main.ts` (into backoffice `lib/`):**

| Block | Destination | Role |
|-------|-------------|------|
| Sample fixtures (`sampleLocations`, `sampleClaims`, etc.) | `lib/sample-data.ts` | Demo data passed into utility calls |
| UI types (`OperationDefinition`, `ParameterDefinition`, etc.) | `lib/operation-types.ts` | Shape of dropdown params and `run()` handlers |
| Param helpers + `buildOperations()` (22 operations) | `lib/operations-registry.ts` | Maps UI labels/defaults to utility invocations |

**What was not copied:** DOM code from `main.ts` (rendering, event listeners, history UI). That behavior lives in React (`hooks/use-manual-test-runner.ts` + `components/manual-test/*`).

**How each operation runs:**

1. `buildOperations()` returns an array of `OperationDefinition` objects — one per M2 function.
2. Each entry defines `id`, `label`, `description`, `params` (with defaults), and a `run(params)` handler.
3. Every `run()` handler **imports and calls** the real utility from `apps/src/utils/*` via `@healthcore/src/*` (e.g. `filterClaims`, `validateClaim`). KPI math and validation rules are not duplicated in backoffice.
4. Sample arrays are imported from `@/lib/sample-data.ts` (copied fixtures), matching the legacy manual test page.

**Public API consumed by the UI:**

- `getOperations()` — cached list of all 22 operations (used to populate the function dropdown).
- `defaultParamValues(operation)` — default param map for “Run all with current defaults”.
- `buildOperations()` — rebuilds the registry (same as `getOperations()` on first call).

**CLI / legacy parity:**

- Command-line manual test remains `npx -y tsx apps/src/main.ts` (uses the registry embedded in `main.ts`).
- Legacy browser page remains `apps/src/index.html` + compiled `dist/main.js`.
- Backoffice is a third consumer of the same operation set; all three can drift if `buildOperations()` changes in only one place.

**Sync expectation:** `operations-registry.ts` opens with a comment pointing to `apps/src/main.ts`. Future edits to operation labels, defaults, or wiring should be applied in both files until a shared extract is done.

- Decision: Import M2 business logic via `@healthcore/src/*` path alias; use webpack build with `extensionAlias` for `.js` specifiers in `apps/src`.
- Why: Turbopack cannot resolve `apps/src` internal `.js` imports without webpack; production verify uses `next build --webpack`.

## Backoffice Cleanup (M2 UI restructure)

- Decision: Nest M2 manual test app at `uis/backoffice/backoffice_functions/`; keep `uis/backoffice/` as umbrella for future internal tools.
- Why: Room for additional backoffice apps without mixing concerns in one Next.js project.

- Decision: Restyle backoffice_functions with `uis/website` sky/teal palette (gradient header, sky-700 CTAs, HealthcoreLogo copy) without adding i18n or public nav.
- Why: Internal tool should feel on-brand with the public portal per stakeholder visual consistency.

## Incident Analyzer

- Decision: Single source of truth for incident validation/aggregation in `uis/incident_analyzer/analysis_core.py`; CLI (`analyze.py`) and FastAPI (`services/api`) both import it.
- Why: Avoid duplicated rules; CLI and API/dashboard must return identical counts and percentages.

- Decision: Incident analyzer CLI dependencies managed with `uv` (`uis/incident_analyzer/pyproject.toml` + `uv.lock`); run via `uv run analyze`. No `requirements.txt` or manual venv.
- Why: Single Python toolchain across API and CLI; avoids pip/uv drift.

- Decision: FastAPI incidents routes under `/api/v1/incidents/` with in-memory `LastAnalysisStore` for export (no DB/auth in v1).
- Why: Internal prototype for Priya's team; matches approved architecture versioning; persistence deferred.

- Decision: Standalone Next.js app at `uis/incident_analyzer` on dev port 3002 (not merged into backoffice or website).
- Why: Isolated internal tool; avoids coupling with M2 manual test UI or public portal.

- Decision: Never expose `patient_id` or row-level PHI in CLI output, API JSON, logs, or export CSV — aggregate counts only.
- Why: HIPAA / UK GDPR compliance requirement from stakeholders (Priya Nair, James Osei).

## Supplier Directory (Milestone 09)

- Decision: Use TinyDB JSON store at `services/api/db.json` as interim persistence (Postgres migration deferred per James Osei).
- Why: Lightweight storage for immediate delivery; aligns with SPECS milestone 09 scope.

- Decision: Follow existing `app/` modular monolith layout (`router` → `service` → `store`) under `app/domains/procurement/suppliers/`, not SPECS' flat `main.py` / `routes.py` structure.
- Why: Consistency with delivered incident analyzer domain; register via `app/api/v1/router.py`.

- Decision: Enforce unique supplier names on POST (422); idempotent seeder dedupes by name.
- Why: Registry must not allow duplicate trade names.

- Decision: Set `rate_updated_at` on seed, POST create, and every PATCH rate (Option A).
- Why: Claire's audit trail requires a visible timestamp from registration onward.

- Decision: Manual seed only (`uv run seed`); no auto-seed on API startup.
- Why: Explicit developer workflow per implementation plan.

- Decision: CORS via settings list including `http://localhost:3003` (not wildcard `*`).
- Why: Match existing `app/core/config.py` pattern.

- Decision: Standalone Next.js app at `uis/supplier_directory` on port 3003; styling copied from `uis/incident_analyzer`.
- Why: Isolated internal tool; visual consistency across HealthCore Digital ops apps.

- Decision: UI uses Actions column for rate edit and status toggle (PATCH only); DELETE is API-only soft suspend.
- Why: Clear edit affordances; preserve audit history without exposing delete in UI.

- Decision: Client-side list filters; API `?country=` / `?category=` still implemented and tested.
- Why: Simple v1 UX with full fetch; API filters available for future consumers.

- Decision: Add `compliance_agreement` table column; humanized category labels; auto-derived currency on add form.
- Why: CONTEXT compliance visibility; readability; reduce form errors.

## Authentication (AUTH-01)

- Decision: JWT HS256 stateless tokens via `python-jose`; passwords hashed with `passlib[bcrypt]`; pin `bcrypt>=4.0.0,<4.1` for passlib compatibility.
- Why: SPECS milestone scope; matches architecture proposal Auth/JWT slice.

- Decision: Extract shared TinyDB access to `app/core/db.py`; suppliers and users tables share `services/api/db.json`.
- Why: Avoid cross-domain imports; enables future `sessions` table without further refactor.

- Decision: Protect `/users` GET/PUT/DELETE and `/auth/me`; keep `POST /users`, `POST /auth/register`, and `POST /auth/login` public.
- Why: SPECS selective protection; admin/RBAC deferred with TODO on DELETE.

- Decision: PUT `/users/{id}` owner-only (403 for other users); DELETE open to any authenticated user until RBAC.
- Why: SPECS authorization model for AUTH-01.

- Decision: Normalize emails to lowercase; block inactive users at login with generic `Invalid credentials`.
- Why: Implementation plan locked decisions for consistent lookups and security.

- Decision: Do not protect `/suppliers` or `/incidents` in AUTH-01; document `include_router(..., dependencies=[Depends(get_current_user)])` pattern in `api/v1/router.py`.
- Why: Incremental rollout; existing frontends continue working without tokens.

