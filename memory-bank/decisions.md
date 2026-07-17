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

## Supplier Directory

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

- Decision: Reject inactive users in `get_current_user` (401 `Could not validate credentials`) in addition to login blocking.
- Why: Prevent deactivated accounts from using still-valid JWTs until expiry.

- Decision: Require `SECRET_KEY` and `JWT_EXPIRE_MINUTES` from environment (no in-code defaults); `.example.env` documents local values.
- Why: Evaluation criterion — signing secret and token expiry must not be hardcoded.

## Authentication (AUTH-02 / AUTH-03)

- Decision: Navigation cards on backoffice landing (`/`) are **hidden until the user is logged in**; logged-out visitors see a public staff-portal info section instead (no internal tool URLs).
- Why: Stakeholder UX — internal app links should not be exposed to unauthenticated users; public view provides context and link to patient website only.

- Decision: Consolidate internal tools as **same-origin routes** on landing (`3001`); deprecate standalone dev servers on 3000–3003 (legacy multi-port era).
- Why: Eliminates cross-port `localStorage` / `?token=` handoff and logout chains; single `AuthGuard`.

- Decision: Hybrid import model — feature UI in sibling folders (`uis/incident_analyzer`, `uis/supplier_directory`, `uis/backoffice/backoffice_functions`, `uis/backoffice/talent-tracker`); landing owns App Router routes.
- Why: Reuse existing components without duplicating Next.js shells.

- Decision: Talent tracker data from **`NEXT_PUBLIC_TRACKER_API_URL`** only; HealthCore JWT guards route access only.
- Why: Tracker API is external; no Bearer on tracker requests.

- Decision: Incident and supplier APIs protected with router-level `Depends(get_current_user)`; frontends use shared `healthcoreFetch` with Bearer from `localStorage`.
- Why: AUTH-02 requires authenticated HealthCore API access for operational tools.

- Decision: Logout clears token and redirects to **`/`** (public hub).
- Why: Consistent post-logout UX across hub, profile, and tool toolbars.

- Decision: Pytest forces **`EMAIL_API_KEY=""`** in `tests/conftest.py` so password-reset tests use stdout fallback regardless of developer `.env`.
- Why: Resend sandbox rejects non-owner recipients; tests must not depend on external email delivery.

- Decision: Public website dev server runs on port **3000** (`uis/website/package.json`); backoffice landing on **3001**.
- Why: Unified port map for local `npm run dev` and Docker Compose — single mental model; public website links on landing resolve without env overrides.

- Decision: Unify local and Docker UI ports (3000 website, 3001 backoffice), superseding the prior 3004/3005 local-only map.
- Why: Fixes backoffice public-website links in both auth states; eliminates `NEXT_PUBLIC_WEBSITE_URL` workaround for the common case.
- Tradeoff: Cannot run Docker UI stack and local `npm run dev` UI simultaneously (API port 8000 conflict remains either way).

## Milestone 5 — Inventory Backend

- Decision: **Dual-database architecture** — TinyDB (`get_db`) for users/auth/suppliers; Supabase PostgreSQL (`get_supabase_db`) for inventory tables only.
- Why: Spec requirement; no user replication in Supabase; `user_uuid` stored as plain string on orders.

- Decision: Supabase project named **`milestone5_inventory`**; schema created via `SQLModel.metadata.create_all()` on startup — no SQL migrations in this milestone.
- Why: Implementation plan; simplest first integration path per James Osei architecture proposal.

- Decision: Inventory domain uses **flat router layout** (`models.py`, `schemas.py`, `router.py`, `seed.py`) — not suppliers' `service/store` layering.
- Why: Milestone 5 spec mandates spec structure; business logic in router with `compute_stock` helper.

- Decision: **Public GETs** on inventory (`/products`, `/products/{id}`, `/orders`); auth required only on POST endpoints.
- Why: Spec §10.3 auth table; stakeholder clarification during planning.

- Decision: Inventory tests use **in-memory SQLite** with `StaticPool` + `check_same_thread=False`; `conftest.py` forces `DATABASE_URL=""`.
- Why: CI/dev pytest must not require live Supabase; avoids thread and connection isolation issues with TestClient.

- Decision: Inventory seed orders inserted **only on first supply insert**; `user_uuid="1"` placeholder with no TinyDB FK.
- Why: Idempotent seed per spec §11.4; order traceability string is operational reference only.

## Milestone 5 — Inventory Frontend

- Decision: Feature module at **`uis/backoffice/inventory/`** aliased into landing (`@backoffice/inventory`) — same hybrid pattern as talent-tracker.
- Why: Reuse landing auth/routing without a standalone dev server; single port 3001.

- Decision: **ToolToolbar only** in inventory layout; footer from root `ConditionalLandingFooter` (not duplicated per-page).
- Why: Matches supplier-directory / incident-analyzer; stakeholder Q&A 2026-07-01.

- Decision: Unknown `clinic_id` values display **`Unknown clinic ({id})`** in order history.
- Why: Seed data includes `clinic_id: 10`; frontend clinic map is IDs 1–6 only; no backend change in this milestone.

- Decision: **Strict ≤80 lines** per component/hook file — split tables, forms, and submit logic into hooks + lib helpers.
- Why: Agent component-size rule; stakeholder Q&A 2026-07-01.

- Decision: Inventory module uses **symlinked `node_modules`** from `landing/` for TypeScript resolution (no separate `package.json`).
- Why: Next.js `externalDir` typecheck requires React types resolvable from module path; matches talent-tracker isolation without duplicating deps.

## Centralized Incident Manager

- Decision: New domain at **`app/domains/incidents/`** (CRUD) alongside unchanged **`reporting/incidents/`** (CSV analyze); both share `/incidents` prefix with route-order care (`/summary` before `/{id}`).
- Why: Spec requires coexistence with Incident Analyzer; no changes to analyze/export routes.

- Decision: DB column **`incident_id`** (nullable, unique) stores CSV `HC-000nnn` for seed idempotency only; API PK remains auto-increment **`id`**; `incident_id` excluded from public schemas.
- Why: Stakeholder clarification; CSV business key vs integer REST id.

- Decision: Seed CSV path **`memory-bank/references/centralized_incident_manager_ai_plan/incidents-healthcore.csv`**; standalone `scripts/seed_incidents.py` only (not `uv run seed`).
- Why: Locked stakeholder answers; plan-folder file is canonical.

- Decision: Summary API returns **zero-filled fixed keys** for status/category/origin; **`by_branch` only keys with count > 0**.
- Why: Leadership dashboard consistency for enums; dynamic branch breakdown.

- Decision: List UI includes **category** filter (fourth dropdown) in addition to status, origin, branch.
- Why: Stakeholder request; API already supported `?category=`.

- Decision: Merge **`feature/critical_error_handling`** for global 500 handler — do not duplicate in incident manager work.
- Why: Handler already delivered on that branch.

- Decision: Feature module **`uis/backoffice/incident-manager/`** with same landing alias / ToolToolbar / ≤80-line component split as inventory.
- Why: Established backoffice hybrid pattern on port 3001.

- Decision: Incident validation extracted to **`packages/shared/python/healthcore_incidents/`** (`healthcore-incidents-shared` uv package); API and `scripts/seed_incidents.py` import shared validators/constants; `analysis_core.py` reuses CSV validation from shared package. Client form validation in **`packages/shared/lib/incident-validation.ts`**.
- Why: Central Incident Manager eval criteria require shared validation without duplication across script, API, and frontend.

## Docker (#infra-40)

- Decision: **Development-only** Docker Compose with exactly two services (`ui`, `api`) on named network `healthcore_net`; no production multi-stage builds in this ticket.
- Why: Ticket scope is developer onboarding, not deployment.

- Decision: Backend image uses **uv** (`uv sync --frozen`) with `UV_PROJECT_ENVIRONMENT=/opt/venv` outside bind-mounted paths; **no `requirements.txt`**.
- Why: Matches existing repo tooling; prevents mount shadowing of installed packages.

- Decision: Single `ui` container runs website and backoffice landing dev servers; aliased modules (inventory, incident-manager, talent-tracker, etc.) compile via landing webpack — no separate containers or ports.
- Why: Spec requirement; mirrors local architecture.

- Decision: **Proactive `npm ci`** for all six active UI apps at image build time with anonymous volumes per `node_modules`.
- Why: First-run reliability for aliased backoffice modules.

- Decision: Root `.env` + `.example.env` for Docker; `services/api/.env` from `services/api/.example.env` for local non-Docker API. Manual backoffice dev: `uis/backoffice/landing/.example.env` → `.env.local` only — aliased modules and `uis/website` do not need their own env files in normal workflow. `JWT_EXPIRE_MINUTES=15` in Docker env.
- Why: Stakeholder clarification; Compose injects process env — no per-app `.env.local` needed in Docker.

- Decision: `NEXT_PUBLIC_*` URLs use `localhost` (browser-facing); `API_URL_INTERNAL` uses `http://api:8000/api/v1` for container-to-container calls.
- Why: Browsers cannot resolve Docker service names.

- Decision: npm-workspaces conversion and `@repo/shared-types` rename deferred post-#infra-40.
- Why: Explicit out-of-scope per plan.

- Decision: Add Compose **`test` profile** service reusing API image/volumes; default command `uv run pytest`. Does not start with `docker compose up`.
- Why: One-shot pytest without requiring the dev stack to be running; `docker compose exec api uv run pytest` retained for iterative dev.

- Decision (Milestone 6 Build 2): Reporting jurisdiction filter for clinic-grain KPIs uses **clinic catalog location** (`CLINICS[].jurisdiction`), not supply-derived telemetry `jurisdiction` alone; UK clinic names added (ids 7–9).
- Why: Supply-country tags can pair UK jurisdiction with US clinics (e.g. San Antonio); filter UX must not show US clinics under UK.

- Decision: Reconcile stakeholder CONTEXT KPIs to three observable metrics — supply consumption rate, supply waste rate, insufficient-stock rejection rate — because `min_stock_threshold`, `emergency` clinical context, and persisted stock levels do not exist in the delivered inventory model.
- Why: Codebase wins over context docs; metrics must be computable from real API paths and event properties.

- Decision: Standard event envelope includes **both** `requestId` and `service: "backoffice"`; `userId` is opaque TinyDB user id as string (`str(user.id)`), not email/name; `schemaVersion` **1.1.0** with v1.1 events.
- Why: Resolves doc conflict across phases; matches inventory `user_uuid` convention.

- Decision: `jurisdiction` derived client-side from `MedicalSupply.country` (`US`→`us`, `UK`→`uk`); not a database column.
- Why: No jurisdiction field on inventory entities; CCO audit segmentation still required on clinic-operation events.

- Decision: v1.1 events — `supply_consumption_form_abandoned` (outbound **partial form** XOR: supply **or** quantity, not both) and `incident_list_filter_applied` (Incident Manager filters; not inventory — no filter UI there).
- Why: Stakeholder additions for form-friction and Patient Experience filter audit; abandon refined during Phase 2 implementation.

- Decision: `product_created` event designed but **not** instrumented in Phase 2 — no create-product UI.
- Why: Phase 2 captures only at frontend `track()` call sites.

- Decision (Phase 2 delivered, `7ce0da5`): Client transport uses `fetch` with `keepalive: true` on tab-close flush (not `sendBeacon` — cross-origin JSON body failed FastAPI parse). Form abandon uses immediate `void flush()`.
- Why: Verified in manual testing; `sendBeacon` without reliable `Content-Type` returned 422.

- Decision (downstream, locked at planning): telemetry ingest `POST /telemetry/events` unauthenticated (`fetch`/`keepalive`, no Bearer); `GET /telemetry/report` JWT-protected; `telemetry_events` on existing `milestone5_inventory` Supabase project.
- Why: Stakeholder clarifications during implementation planning.

- Decision (Phase 3 delivered): `telemetry_events.tags` uses PostgreSQL `jsonb` (SQLite `JSON` in tests); startup runs `ALTER COLUMN tags TYPE jsonb` + GIN index `idx_telemetry_events_tags`.
- Why: Default SQLAlchemy `JSON` maps to `json` in Postgres, which cannot use GIN without an operator class; `jsonb` matches storage spec and enables tag containment queries.

- Decision (DEV-53 nightly export): Orchestration status lives in a separate `job_runs` table (`pending`/`processing`/`completed`/`failed`); do **not** harmonize with `pipeline_runs` vocabulary or add an FK between them.
- Why: Different layers (job lock/idempotency vs ETL audit); rubric grades independence.

- Decision (DEV-53): Trigger is OS crontab only (`0 2 * * *`); `processing` status is the lock; stale locks reclaim after `STALE_LOCK_HOURS` (default 6) with no extra lock table/column.
- Why: Avoids zombie `processing` rows after SIGKILL while satisfying “no second locking mechanism.”

- Decision (DEV-53): `scripts/nightly_export.py` bootstraps env from repo-root `.env` then fills gaps from `services/api/.env` before importing `app.core.*`.
- Why: Docker uses root `.env`; manual API uses `services/api/.env`; cron must work for both without FastAPI.
