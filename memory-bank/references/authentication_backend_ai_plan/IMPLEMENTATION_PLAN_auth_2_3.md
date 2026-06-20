---
name: AUTH-02 / AUTH-03 Implementation Plan
overview: "Deliver backoffice landing app (login, register, account management, nav hub) at uis/backoffice/landing/ on port 3004; internal tools as same-origin routes (not separate ports); password-reset API; HealthCore JWT on services/api for incidents/suppliers."
todos:
  - id: step1-scaffold-landing
    content: "Scaffold uis/backoffice/landing/ (Next.js 16, port 3004) with globals, layout, hero"
    status: completed
  - id: step2-backend-name-field
    content: "Add name field to user schemas/services; expand CORS defaults in config + .example.env"
    status: completed
  - id: step3-login
    content: "Login page + lib/api.ts apiFetch wrapper"
    status: completed
  - id: step4-register
    content: "Registration page with client-side validation"
    status: completed
  - id: step5-landing-auth-guard
    content: "Auth guard + (public)/(protected) route groups on landing app"
    status: completed
  - id: step6-account-pages
    content: "Profile and change-password pages"
    status: completed
  - id: step7-backend-reset
    content: "POST /auth/forgot-password and /auth/reset-password + email/stdout + used_reset_tokens table"
    status: completed
  - id: step8-reset-frontend
    content: "Forgot-password and reset-password pages"
    status: completed
  - id: step9-nav-cards
    content: "Navigation card grid + conditional logged-in hero UI + internal route links (no cross-port tokens)"
    status: completed
  - id: step10-0-plumbing
    content: "Landing plumbing — aliases, AuthGuard, nav-apps routes, relocate talent-tracker, update SPECS_auth_2_3.md"
    status: completed
  - id: step10-1-backoffice-functions
    content: "Migrate backoffice-functions → /backoffice-functions route under landing"
    status: completed
  - id: step10-2-incident-analyzer
    content: "Migrate incident-analyzer → /incident-analyzer + apiFetch Bearer + protect /incidents API"
    status: completed
  - id: step10-3-supplier-directory
    content: "Migrate supplier-directory → /supplier-directory + apiFetch Bearer + protect /suppliers API"
    status: completed
  - id: step10-4-talent-tracker
    content: "Migrate talent-tracker → /talent-tracker (external tracker API; route guard only)"
    status: completed
  - id: step10-5-cleanup
    content: "Deprecate standalone tool shells; interim README/CORS; remove tool icon.svg; memory-bank interim"
    status: completed
  - id: step11-website-port
    content: "CANCELLED — folded into Step 13 (website dev on port 3005)"
    status: cancelled
  - id: step12-favicon
    content: "HealthCore PNG favicon on landing (3004) and website (3005); verify on hub + tool route"
    status: pending
  - id: step13-integration
    content: "Final UAT checklist, README/API docs rewrite, pytest sign-off, milestone delivered"
    status: pending
isProject: false
---

# AUTH-02 / AUTH-03 — Implementation Plan

**Plan file:** [`IMPLEMENTATION_PLAN_auth_2_3.md`](IMPLEMENTATION_PLAN_auth_2_3.md)

**Requirements source:** [`SPECS_auth_2_3.md`](SPECS_auth_2_3.md) — **SPECS will be updated** to match this plan before Step 10 build begins.

**Prior milestone:** [`IMPLEMENTATION_PLAN_auth_1.md`](IMPLEMENTATION_PLAN_auth_1.md) / [`SPECS_auth_1.md`](SPECS_auth_1.md) (delivered)

**Status:** In progress — Steps 1–8 delivered; Steps 9–10 revised for **single-origin route consolidation** (stakeholder decision, 2026-06).

**Agent workflow:** Per [`AGENTS.md`](../../../AGENTS.md) — bootstrap memory-bank root files, re-sync `progress.md` and `decisions.md` at each step gate. **Stop after every Step 10 sub-step** for manual UAT before continuing.

---

## Executive summary

AUTH-02 adds a **central backoffice app** at `uis/backoffice/landing/` (port **3004**) that provides login, registration, account management, navigation, and **hosts all internal tools as same-origin routes**. AUTH-03 adds **password reset** (backend endpoints + frontend flows).

### Architecture change (Step 10 — locked)

Internal tools are **not** separate dev servers on ports 3000–3003. Instead:

- **One Next.js app** runs on **3004** (landing).
- Tool UI code lives in **sibling feature folders** under `uis/backoffice/` (hybrid import model).
- Landing defines App Router routes that import components from those folders.
- **No cross-port `localStorage`**, no `?token=` handoff, no per-app AuthGuard copies, no cross-app logout chain.

| Route | Feature module | Data API |
|-------|----------------|----------|
| `/incident-analyzer` | `uis/backoffice/incident-analyzer/` | `services/api` `:8000` + HealthCore JWT |
| `/supplier-directory` | `uis/backoffice/supplier-directory/` | `services/api` `:8000` + HealthCore JWT |
| `/talent-tracker` | `uis/backoffice/talent-tracker/` (relocated from `apps/`) | External tracker API (separate env var) |
| `/backoffice-functions` | `uis/backoffice/backoffice-functions/` | None (`apps/src` utils) |

The public website (`uis/website/`, port **3005**) remains a **separate app** with no auth.

---

## Dependency on AUTH-01 (delivered baseline)

| AUTH-01 asset | AUTH-02/03 usage |
|---------------|------------------|
| `POST /auth/register`, `/auth/login`, `GET /auth/me` | Landing auth flows |
| `PUT /users/{id}` with password field | Change-password page |
| `get_current_user` + JWT HS256 | Token validation; reset tokens reuse `settings.secret_key` |
| `app/core/db.py` TinyDB singleton | `used_reset_tokens` table |
| `hash_password()` / `verify_password()` | Reset-password endpoint |

`/suppliers` and `/incidents` gain **`get_current_user` protection** during Step 10.2 / 10.3. Incident and supplier frontends send `Authorization: Bearer <token>` via landing `apiFetch`.

---

## Port map (revised — locked)

| Service | Path | Port | Notes |
|---------|------|------|-------|
| **Backoffice (all internal tools + auth hub)** | `uis/backoffice/landing/` | **3004** | Single dev server |
| Public Website | `uis/website/` | **3005** | No auth; set in Step 13 |
| HealthCore API | `services/api/` | **8000** | Auth, incidents, suppliers |
| External Talent API | (remote) | — | `NEXT_PUBLIC_TRACKER_API_URL` |

**Deprecated for local dev:** separate Next.js processes on 3000–3003. Feature folders remain as import sources, not runnable apps.

---

## Folder structure (target after Step 10)

```text
uis/backoffice/
├── landing/                         ← only Next.js app (port 3004)
│   └── app/
│       ├── (public)/              ← hub, login, register, reset
│       └── (protected)/
│           ├── layout.tsx           ← AuthGuard (session check once)
│           ├── account/...
│           ├── incident-analyzer/   ← route + optional nested layout
│           ├── supplier-directory/
│           ├── talent-tracker/
│           └── backoffice-functions/
├── incident-analyzer/               ← components, lib, hooks (no standalone app/)
├── supplier-directory/
├── talent-tracker/                  ← relocated from apps/talent-pipeline-tracker/
└── backoffice-functions/
```

---

## Planning decisions (locked)

| Topic | Decision |
|-------|----------|
| Internal tool hosting | **Same-origin routes** on landing (`3004`); hybrid **import** from sibling folders |
| Route paths | `/incident-analyzer`, `/supplier-directory`, `/talent-tracker`, `/backoffice-functions` |
| Layout pattern | **Option B** — `(protected)/layout.tsx` = AuthGuard only; each tool has nested `layout.tsx` for tool chrome (header, logout) |
| Nav cards (Step 9 update) | Internal `<Link href="...">` paths; **no** `?token=`, **no** `target="_blank"` for internal tools |
| Cross-port auth | **Removed** — no URL token passing, no cross-app logout chain, no per-port AuthGuard |
| Logout | `localStorage.removeItem('token')` → redirect to **`/`** (public hub with Log In / Register) |
| `LOGIN_URL` | Relative **`/login`** (same origin) |
| Talent tracker API | **External** — `NEXT_PUBLIC_TRACKER_API_URL`; **do not** send HealthCore JWT to tracker API |
| Talent tracker route access | Protected by landing AuthGuard (must be logged into backoffice) |
| HealthCore API tools | Incident + supplier use `apiFetch` + Bearer; backend protects `/incidents` and `/suppliers` |
| Backoffice functions | No HealthCore API; imports `@healthcore/src` utils via existing alias pattern |
| Email provider | **Resend**; stdout fallback when `EMAIL_API_KEY` empty |
| Reset token TTL | **30 minutes** |
| Step 11 (website port) | **Cancelled** as standalone step — website `--port 3005` in Step 13 |
| Step gate | Stop after **each Step 10 sub-step** for manual UAT |
| Standalone tool apps | Deprecate after migration (Step 10.5); landing routes are canonical |

---

## Implementation sequence

Follow step order. **Stop after each step** (especially 10.0–10.4) for manual testing before proceeding.

### Steps 1–8 — Delivered

Steps 1–8 are complete (landing scaffold through password reset UI). See git history and `memory-bank/progress.md`.

**Note:** Step 5 AuthGuard currently protects `/account/*` only. Step 10.0 extends the same guard to all `(protected)` tool routes.

---

### Step 9 — Navigation cards + conditional landing UI

**Goal:** Hub page with tool links and logged-in hero.

**Landing page behavior:**

- **Logged out:** public intro section (staff portal info, bullets, link to public website on `:3005`) — **no nav cards**
- **Logged in:** navigation card grid linking to **internal routes**:
  - `/incident-analyzer`
  - `/supplier-directory`
  - `/talent-tracker`
  - `/backoffice-functions`
  - Public Website → `http://localhost:3005` (external, same tab, no lock)
- Protected cards: lock icon; **same-tab** internal links (no token query param)
- Logged-in hero: "Welcome, {name}", My Profile + Log Out
- Logged-out hero: Log In + Register
- On mount when token present: `GET /auth/me`; 401 clears token

**Files:** Update `lib/nav-apps.ts`, `components/landing/nav-card.tsx`, `nav-cards.tsx` as needed.

**Verify:** Logged out → public content only. Logged in → nav cards with **relative paths** (routes may 404 until Step 10 migrations — acceptable if documented at gate).

**Gate:** Stop for UAT before Step 10.

---

### Step 10 — Consolidate internal tools as landing routes + auth

**Goal:** All internal tools accessible only via landing on port **3004**; single AuthGuard; HealthCore Bearer on incident/supplier API calls.

**Do NOT modify `uis/website/` auth (it stays public).**

---

#### Step 10.0 — Plumbing (before first tool migration)

**Goal:** Landing can import from sibling feature folders; nav cards point at real routes; talent tracker relocated.

**Actions:**

1. **Relocate** `apps/talent-pipeline-tracker/` → `uis/backoffice/talent-tracker/` (preserve components, lib, types; Next.js `app/` shell deprecated later).
2. **Landing `next.config.ts` + `tsconfig.json`:**
   - `transpilePackages` or path aliases for sibling folders, e.g.:
     - `@backoffice/incident-analyzer/*` → `../incident-analyzer/*`
     - `@backoffice/supplier-directory/*` → `../supplier-directory/*`
     - `@backoffice/talent-tracker/*` → `../talent-tracker/*`
     - `@backoffice/backoffice-functions/*` → `../backoffice-functions/*`
   - Backoffice functions: inherit `@healthcore/src` webpack/turbopack alias from existing `backoffice_functions` config.
3. **Extend `(protected)/layout.tsx`** — single `AuthGuard` for all protected routes (account + tools). Remove `?token=` ingestion from guard (same origin).
4. **Update `lib/nav-apps.ts`** — `url` fields become paths (`/incident-analyzer`, etc.) for internal tools.
5. **Env vars** in landing `.env.local.example`:
   - `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1` (HealthCore)
   - `NEXT_PUBLIC_TRACKER_API_URL=https://playground.4geeks.com/tracker/api/v1` (talent tracker)
6. **Stub routes** (optional): placeholder pages at each tool path confirming auth works.
7. **Update `SPECS_auth_2_3.md`** — align with this plan (single-origin routes, drop cross-port token passing, revised port map). Step 13 verifies alignment only; do not defer SPECS to Step 13.

**Verify:**

- `npm run verify` in landing passes.
- Log in → `/account/profile` still works.
- Direct visit to `/incident-analyzer` without token → redirect `/login`.

**Gate:** Stop for UAT.

---

#### Step 10.1 — Backoffice Functions → `/backoffice-functions`

**Goal:** M2 manual test dashboard available at `/backoffice-functions`.

**Actions:**

1. Add `app/(protected)/backoffice-functions/layout.tsx` — tool header + logout button.
2. Add `app/(protected)/backoffice-functions/page.tsx` — import/render `ManualTestPage` from `@backoffice/backoffice-functions/`.
3. Move or re-export components from `uis/backoffice/backoffice_functions/` into `uis/backoffice/backoffice-functions/` if folder rename is part of normalize (or keep folder name and alias only — pick one convention and document).

**API:** None.

**Verify:**

- Nav card → `/backoffice-functions` loads when logged in.
- Logged out → redirect `/login`.
- Function runner works (same as former `:3001` app).

**Gate:** Stop for UAT.

---

#### Step 10.2 — Incident Analyzer → `/incident-analyzer`

**Goal:** CSV upload dashboard at `/incident-analyzer` with authenticated HealthCore API calls.

**Actions:**

1. Nested layout with `IncidentHeader` + logout.
2. Route page imports `IncidentDashboard` from feature folder.
3. Update feature `lib/api.ts` to use landing `apiFetch` (or shared helper) with Bearer token.
4. **Backend:** Enable `get_current_user` on incidents router in `app/api/v1/router.py`.
5. **Tests:** Unauthenticated `POST /api/v1/incidents/analyze` → 401.

**Verify:**

- Upload CSV, analysis, export — all with API on `:8000` and user logged in.
- Without login → cannot reach route.

**Gate:** Stop for UAT.

---

#### Step 10.3 — Supplier Directory → `/supplier-directory`

**Goal:** Supplier registry at `/supplier-directory` with authenticated HealthCore API calls.

**Actions:**

1. Nested layout with `SupplierHeader` + logout.
2. Route pages for list and `/supplier-directory/suppliers/[id]` (or flatten to `/supplier-directory/[id]` — match existing UX).
3. Feature `lib/api.ts` → `apiFetch` + Bearer.
4. **Backend:** Enable `get_current_user` on suppliers router.
5. **Tests:** Unauthenticated supplier endpoints → 401.

**Verify:** CRUD/list flows work; auth enforced on route and API.

**Gate:** Stop for UAT.

---

#### Step 10.4 — Talent Tracker → `/talent-tracker`

**Goal:** Recruiting UI at `/talent-tracker`; route protected by HealthCore session; data from **external tracker API**.

**Actions:**

1. Relocate complete (if not done in 10.0).
2. Nested layout with logout bar / page header pattern.
3. Routes: list, `/talent-tracker/candidates/new`, `/talent-tracker/candidates/[id]`, edit — preserve existing URL structure under prefix.
4. Feature `lib/api.ts` uses **`NEXT_PUBLIC_TRACKER_API_URL` only** — no HealthCore Bearer on tracker requests.
5. Landing AuthGuard ensures user is logged into backoffice before viewing tool.

**Verify:**

- Candidate list/detail/edit/new work against tracker API.
- Logged out → redirect `/login`.
- HealthCore API not required for tracker data calls.

**Gate:** Stop for UAT.

---

#### Step 10.5 — Cleanup (interim)

**Goal:** Remove confusion from deprecated multi-port setup. **Final doc polish and milestone sign-off happen in Step 13.**

**Actions:**

1. Remove or gut standalone `app/` + `next.config.ts` dev scripts from feature folders (or add `README.md` in each: "Run via landing only").
2. Remove leftover `app/icon.svg` / favicon metadata from deprecated tool shells (Step 12 covers landing + website only).
3. **Interim** root `README.md` update — port table (3004, 3005, 8000) and route paths; full README rewrite completed in Step 13.
4. Update `memory-bank/progress.md` and `memory-bank/decisions.md` with Step 10 completion status.
5. Remove obsolete cross-port auth documentation from repo (if present).
6. CORS in `services/api`: ensure `http://localhost:3004` in defaults; remove 3000–3003 if no longer needed. Document in `services/api/README.md` (full update in Step 13).

**Verify:** `npm run verify` on landing; manual smoke of all four tool routes.

**Gate:** Stop for UAT before Step 12.

---

### Step 11 — Website port fix — **CANCELLED**

**Reason:** Internal tools no longer use port 3000. The only remaining port assignment is public website on **3005**, handled in **Step 13** (one-line `package.json` change + README).

---

### Step 12 — Favicon (revised scope)

**Goal:** HealthCore PNG favicon on the two Next.js apps that still run as separate dev servers.

| App | Port | Action |
|-----|------|--------|
| `uis/backoffice/landing/` | 3004 | Verify existing `icon.tsx` + `apple-icon.tsx` + `/favicon.ico` redirect |
| `uis/website/` | 3005 | Add/replace PNG favicon pattern (`icon.tsx`, `apple-icon.tsx`, redirect) |

**Out of scope:** Standalone tool feature folders (former 3000–3003) — landing favicon covers all backoffice routes on `:3004`. Remove leftover `icon.svg` from deprecated tool shells in **Step 10.5**, not here.

**Canonical pattern** (already on landing):

| File | Purpose |
|------|---------|
| `app/icon.tsx` | 32×32 PNG via `next/og` `ImageResponse` |
| `app/apple-icon.tsx` | 180×180 Apple touch icon |
| `next.config.ts` | Redirect `/favicon.ico` → `/icon` |

**Verify:**

1. Hub `/` on `:3004` — tab shows HealthCore logo after hard refresh (**Ctrl+Shift+R**).
2. Logged-in tool route (e.g. `/incident-analyzer`) — **same** favicon (same origin).
3. Public website on `:3005` — tab shows HealthCore logo.
4. `curl -sI http://localhost:3004/icon` and `:3005/icon` return `200` with `content-type: image/png`.

**Gate:** Stop for UAT before Step 13.

---

### Step 13 — Final integration UAT + docs

**Goal:** Milestone sign-off for AUTH-02/03. **Assumes Steps 10–12 complete.** Step 10.5 handles interim cleanup; Step 13 is the final documentation pass and full regression checklist.

#### Manual checklist

**Auth & hub**

1. Register → welcome + nav cards on `/`.
2. Logged out → public intro only; no internal tool URLs exposed.
3. Each nav card → correct route (`/incident-analyzer`, `/supplier-directory`, `/talent-tracker`, `/backoffice-functions`); **no `?token=` in URL**.
4. Direct visit to each protected route without session → `/login`.
5. Profile → edit name → save.
6. Change password → success.
7. Logout from hub → `/` with Log In / Register.
8. Logout from each tool header → `/` with Log In / Register.
9. Forgot password → reset → login with success banner.

**Tools**

10. `/backoffice-functions` — function runner works.
11. `/incident-analyzer` — CSV upload, analysis, export (API `:8000` + Bearer).
12. `/supplier-directory` — list, add, detail route (confirm final path: `/supplier-directory/suppliers/[id]` or flattened).
13. `/talent-tracker` — list, `/talent-tracker/candidates/new`, `/talent-tracker/candidates/[id]`, edit.
14. Talent tracker uses **`NEXT_PUBLIC_TRACKER_API_URL` only** — no HealthCore Bearer on tracker requests.

**API & security**

15. Incident + supplier API calls return **401** when token cleared (browser or curl without Bearer).
16. `uv run pytest` in `services/api/` — full suite green (includes protected route tests from Steps 10.2/10.3).

**Public & polish**

17. Public website on **3005** — no auth prompts.
18. Favicon visible on `:3004` (hub + tool route) and `:3005`.
19. `SPECS_auth_2_3.md` matches implemented behavior (updated in Step 10.0; verify only here).

#### Docs updates (final pass)

| File | Changes |
|------|---------|
| Root `README.md` | **Replace** per-app port sections (3000–3003) with single backoffice section: one `npm run dev` on landing (`3004`), **route table**, env vars (`NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_TRACKER_API_URL`), note talent tracker path `uis/backoffice/talent-tracker/` |
| `services/api/README.md` | `/incidents` and `/suppliers` require Bearer auth; CORS defaults `http://localhost:3004` only; reset endpoints and env vars |
| `uis/website/package.json` | `"dev": "next dev --port 3005"` if not already set |
| `memory-bank/progress.md` | AUTH-02/03 **delivered** |
| `memory-bank/decisions.md` | Single-origin consolidation, route paths, talent API split, logout → `/` |

#### Playwright (optional)

Scope to **landing only** (`uis/backoffice/landing/`): login, register, forgot-password → reset-password redirect. Tool routes covered by manual UAT above.

**Gate:** Milestone complete.

## Auth model (single origin)

```text
Browser @ localhost:3004
├── (public)/          → no guard
│   ├── /              → hub (logged-in or public intro)
│   ├── /login
│   └── /register, /forgot-password, /reset-password
└── (protected)/       → AuthGuard checks localStorage "token"
    ├── /account/*
    ├── /incident-analyzer/*
    ├── /supplier-directory/*
    ├── /talent-tracker/*
    └── /backoffice-functions/*
```

**Logout:** Clear token → `window.location.href = '/'`.

**401 from apiFetch:** Clear token → redirect `/login`.

---

## API wiring summary

| Tool | Route guard | HTTP client | Backend |
|------|-------------|-------------|---------|
| Backoffice Functions | HealthCore JWT | N/A | Local TS utils |
| Incident Analyzer | HealthCore JWT | `apiFetch` + Bearer | `services/api` `/incidents/*` |
| Supplier Directory | HealthCore JWT | `apiFetch` + Bearer | `services/api` `/suppliers/*` |
| Talent Tracker | HealthCore JWT | Feature `fetch` to tracker base URL | External tracker API |

---

## Risk register

| Risk | Mitigation |
|------|------------|
| Large refactor in Step 10 | Incremental sub-steps with UAT gates |
| Path alias / import breaks build | Step 10.0 plumbing + verify before migrations |
| Talent tracker relocation breaks imports | Move early in 10.0; update docs/scripts paths |
| XSS + localStorage token theft | Accepted per SPECS; HttpOnly deferred |
| Tracker API unrelated to HealthCore auth | Document two-layer model (route vs data API) |
| CORS misconfiguration | Keep `3004` in API CORS defaults |
| Step 9 nav links 404 before Step 10 | Expected; gate Step 9 after cards updated, complete routes in 10.x |

---

## Clarifying questions — resolved (architecture pivot)

| # | Question | Answer |
|---|----------|--------|
| 1 | Integration model | **C — Hybrid:** UI in sibling folders; landing owns routes |
| 2 | URL paths | `/incident-analyzer`, `/supplier-directory`, `/talent-tracker`, `/backoffice-functions` |
| 3 | Layout pattern | **Option B** — auth parent + per-tool nested layout |
| 4 | Standalone apps | **Deprecate** after migration; landing is canonical |
| 5 | Public website | **Separate** on port 3005 |
| 6 | Talent tracker location | **Relocate** to `uis/backoffice/talent-tracker/` |
| 7 | Cross-port auth | **Drop** — single origin, no token handoff |
| 8 | Talent API | **External env var**; HealthCore JWT for route access only |
| 9 | Step 11 | **Cancelled** — website port in Step 13 |
| 10 | Migration pace | **Incremental** — stop after each 10.x for testing |

---

## References

- [AGENTS.md](../../../AGENTS.md)
- [SPECS_auth_2_3.md](SPECS_auth_2_3.md) — update before Step 10 build
- [SPECS_auth_1.md](SPECS_auth_1.md)
- [IMPLEMENTATION_PLAN_auth_1.md](IMPLEMENTATION_PLAN_auth_1.md)
- Style reference: `uis/incident_analyzer/` (feature module layout)
- Existing auth backend: `services/api/app/domains/auth/`
