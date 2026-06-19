---
name: AUTH-02 / AUTH-03 Implementation Plan
overview: "Deliver backoffice landing app (login, register, account management, nav hub) at uis/backoffice/landing/, password-reset API endpoints, cross-app auth guards, and CORS/port updates — building on AUTH-01 backend."
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
    content: "Navigation card grid + conditional logged-in hero UI + token-appended links"
    status: pending
  - id: step10-cross-app-guards
    content: "Copy AuthGuard into backoffice_functions, incident_analyzer, supplier_directory, talent-pipeline-tracker"
    status: pending
  - id: step11-website-port
    content: "uis/website dev script → port 3005 (no auth changes)"
    status: pending
  - id: step12-favicon
    content: "Repository-wide HealthCore PNG favicon (icon.tsx + apple-icon.tsx + favicon.ico redirect) on all Next.js apps"
    status: pending
  - id: step13-integration
    content: "Full integration test pass; update memory-bank progress/decisions; README"
    status: pending
isProject: false
---

# AUTH-02 / AUTH-03 — Implementation Plan

**Plan file:** [`IMPLEMENTATION_PLAN_auth_2_3.md`](IMPLEMENTATION_PLAN_auth_2_3.md)

**Requirements source:** [`SPECS_auth_2_3.md`](SPECS_auth_2_3.md)

**Prior milestone:** [`IMPLEMENTATION_PLAN_auth_1.md`](IMPLEMENTATION_PLAN_auth_1.md) / [`SPECS_auth_1.md`](SPECS_auth_1.md) (delivered)

**Status:** In progress — Step 4 delivered (registration page)

**Agent workflow:** Per [`AGENTS.md`](../../../AGENTS.md) — bootstrap memory-bank root files (`projectbrief.md`, `techContext.md`, `progress.md`, `conventions.md`, `decisions.md`), then read applicable `.agents/rules/` and `.agents/skills/` before Step 1. Re-sync `progress.md` and `decisions.md` at each step gate.

---

## Executive summary

AUTH-02 adds a **central backoffice landing app** at `uis/backoffice/landing/` (port **3004**) that provides login, registration, account management, and navigation to all internal HealthCore tools. AUTH-03 adds **password reset** (backend endpoints + frontend flows).

This milestone extends the AUTH-01 FastAPI backend (`services/api`) with:

1. **`name` field** on user records (schemas, register, users CRUD, `/auth/me` response).
2. **Password reset endpoints** — `POST /auth/forgot-password`, `POST /auth/reset-password` with JWT reset tokens, used-token tracking in TinyDB, and transactional email (Resend or SendGrid) with stdout fallback for local dev.
3. **CORS + config** — all app ports (3000–3005), `EMAIL_API_KEY`, `FRONTEND_URL`.

Frontend deliverables:

1. **New Next.js app** — landing, auth views, account pages, shared `lib/api.ts`.
2. **Client-side auth guards** — copied into four protected apps; URL token passing for cross-port `localStorage` isolation.
3. **Website port fix** — `uis/website` dev on port 3005 only (no auth logic).

The public website (`uis/website/`) must remain **entirely unchanged** except the dev port.

HIPAA production architecture (HttpOnly cookies, opaque sessions) documented in SPECS §HIPAA is **informational only** — out of scope.

---

## Dependency on AUTH-01 (delivered baseline)

| AUTH-01 asset | AUTH-02/03 usage |
|---------------|------------------|
| `POST /auth/register`, `/auth/login`, `GET /auth/me` | Landing app auth flows |
| `PUT /users/{id}` with password field | Change-password page |
| `get_current_user` + JWT HS256 | Token validation; reset tokens reuse `settings.secret_key` |
| `app/core/db.py` TinyDB singleton | New `used_reset_tokens` table |
| `hash_password()` / `verify_password()` | Reset-password endpoint |
| `UserCreate` without `name` today | Extend with `name` field |

Existing `/suppliers` and `/incidents` routes gain **`get_current_user` protection** in this milestone (stakeholder decision — extends SPECS). Frontend apps must send `Authorization: Bearer <token>` on all API calls.

---

## Port map (locked by SPECS)

| App | Path | Port |
|-----|------|------|
| Talent Pipeline Tracker | `apps/talent-pipeline-tracker/` | 3000 |
| Backoffice Functions | `uis/backoffice/backoffice_functions/` | 3001 |
| Incident Analyzer | `uis/incident_analyzer/` | 3002 |
| Supplier Directory | `uis/supplier_directory/` | 3003 |
| **Backoffice Landing (new)** | `uis/backoffice/landing/` | **3004** |
| Public Website | `uis/website/` | **3005** (dev script update) |
| API | `services/api/` | 8000 |

---

## Planning decisions (locked)

| Topic | Decision |
|-------|----------|
| Email provider | **Resend** (`resend` pip package); stdout fallback when `EMAIL_API_KEY` empty |
| Reset token TTL | **30 minutes** — separate JWT with `purpose: "reset"` |
| `LOGIN_URL` in AuthGuard | Hardcode `http://localhost:3004/login` per SPECS |
| Talent tracker | Wire HealthCore JWT into tracker API calls where applicable (extends SPECS UI-guard-only scope) |
| API route protection | **Protect `/suppliers` and `/incidents`** with `get_current_user` — extends SPECS; requires token headers in incident_analyzer and supplier_directory frontends |
| Layout + metadata | Root layouts stay server components; thin client `AuthGuardLayout` wrapper |
| Step gate | Stop after each SPECS step for manual UAT before continuing |
| Frontend tests | **Manual step-gated UAT + Playwright smoke tests** for login/register/reset |
| Existing users without `name` | `to_user_response()` defaults `name` to `""` |
| Backend tests | pytest for forgot/reset, name field, and protected route regression |

---

## Implementation sequence

Follow SPECS order exactly. **Stop after each step** for manual testing before proceeding.

### Step 1 — Scaffold landing app

**Goal:** Runnable Next.js shell on port 3004 matching incident analyzer styling.

**Actions:**

- Create `uis/backoffice/landing/` by copying toolchain from `uis/incident_analyzer/`:
  - `package.json` — scripts with `--port 3004` on `dev` and `start`
  - `tsconfig.json`, `next.config.ts`, `postcss.config.mjs`, `eslint.config.mjs`, `.gitignore`
- Copy `app/globals.css` CSS variables from incident analyzer.
- Add components: `healthcore-logo.tsx` (copy), `landing-header.tsx`, `landing-footer.tsx`.
- Root `app/layout.tsx` — header + footer + `{children}`.
- Minimal `app/(public)/page.tsx` — hero only ("HealthCore Back Office" + Login/Register CTAs).
- `.env.local.example` with `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1`.

**Verify:** `cd uis/backoffice/landing && npm install && npm run dev` → http://localhost:3004

---

### Step 2 — Backend: `name` field + CORS

**Goal:** Registration accepts name; `/auth/me` returns it; CORS covers all ports.

**Backend files:**

| File | Change |
|------|--------|
| `app/domains/auth/schemas.py` | Add `name: str = ""` to `UserCreate`; `name: str \| None = None` to `UserUpdate`; `name: str` to `UserResponse` and `User` |
| `app/domains/auth/service.py` | Include `"name": body.name` in register `doc` |
| `app/domains/users/service.py` | Include name in `create_user()`; `to_user_response()` → `payload.setdefault("name", "")` |
| `app/core/config.py` | Default `cors_origins` → all six localhost ports |
| `.example.env` | Full CORS list (prep for Step 7 email vars) |

**Tests:** Extend `tests/test_auth.py` — register with name, `/auth/me` returns name, legacy user without name gets `""`.

**Verify:** `uv run pytest` — full suite green.

---

### Step 3 — Login page

**Goal:** Working login with token storage and redirect.

**Files:**

- `lib/api.ts` — `apiFetch` per SPECS (401 → clear token, redirect `/login`).
- `app/(public)/login/page.tsx` — email/password form, error states, links to register/forgot-password.
- `?reset=success` green banner.

**Verify:** Register user via curl/API, log in via UI, token in `localStorage` key `"token"`, redirect to `/`.

---

### Step 4 — Registration page

**Goal:** Four-field register form with client validation.

**Files:**

- `app/(public)/register/page.tsx` — name, email, password, confirm; field-level errors; 422 handling.

**Verify:** Register new user via UI → auto-login → redirect `/`.

---

### Step 5 — Auth guard on landing app (account routes only)

**Goal:** Route groups; `/account/*` protected.

**Files:**

- `components/auth/auth-guard.tsx` — URL `?token=` ingestion + localStorage check + redirect to `http://localhost:3004/login`.
- `app/(public)/layout.tsx` — passthrough.
- `app/(protected)/layout.tsx` — wraps `<AuthGuard>`.
- Placeholder `account/profile/page.tsx` and `account/change-password/page.tsx`.

**Verify:** Visit `/account/profile` without token → redirect login.

---

### Step 6 — Profile and change-password pages

**Goal:** Account management complete.

**Profile (`/account/profile`):**

- `GET /auth/me` on mount; display name, email (read-only), created_at.
- Inline name edit → `PUT /users/{id}` with `{ name }`.
- Links: change password, logout.

**Change password (`/account/change-password`):**

- Verify current password via `POST /auth/login`.
- Update via `PUT /users/{id}` with `{ password }`.
- Client validation: min 8 chars, match, differ from current.

**Verify:** Full account lifecycle (edit name, change password, logout).

---

### Step 7 — Backend: password reset (AUTH-03)

**Goal:** Forgot/reset endpoints with email or stdout fallback.

**New / modified backend:**

| File | Change |
|------|--------|
| `pyproject.toml` | Add `resend` (or `sendgrid`) |
| `app/core/config.py` | `email_api_key: str = ""`, `frontend_url: str = "http://localhost:3004"` |
| `.example.env` | `EMAIL_API_KEY`, `FRONTEND_URL`, full `CORS_ORIGINS` |
| `app/domains/auth/schemas.py` | `ForgotPasswordRequest/Response`, `ResetPasswordRequest/Response` |
| `app/domains/auth/service.py` | `create_reset_token()`, `send_reset_email()`, `is_token_used()`, `mark_token_used()`, `forgot_password()`, `reset_password()` |
| `app/domains/auth/token.py` | `create_reset_token()` / `decode_reset_token()` with `purpose == "reset"` check |
| `app/domains/auth/router.py` | `POST /forgot-password`, `POST /reset-password` |

**Behavior highlights:**

- Forgot: always 200 with generic message (no enumeration).
- No `EMAIL_API_KEY`: log reset URL to stdout.
- Reset: reject reused tokens via `used_reset_tokens` TinyDB table; hash new password; mark token used.

**Tests:** New cases in `tests/test_auth.py`:

- Forgot unknown email → 200 generic message.
- Forgot known email → stdout log or mock send.
- Reset valid token → password changes, login works.
- Reset reused/invalid/expired token → 400.
- Reset token with wrong `purpose` → 400.

**Verify:** curl forgot → extract token from stdout → curl reset → login with new password.

---

### Step 8 — Frontend: password reset pages

**Goal:** Complete forgot/reset UX.

**Files:**

- `app/(public)/forgot-password/page.tsx` — submit once, disable button, generic confirmation.
- `app/(public)/reset-password/page.tsx` — read `?token=`, validate passwords, redirect `/login?reset=success`.

**Verify:** End-to-end reset flow through UI.

---

### Step 9 — Navigation cards + conditional landing UI

**Goal:** Hub page with tool links and logged-in hero.

**Landing page additions:**

- **Logged out:** public view section (staff portal info, bullets, link to public website on :3005) — **no nav cards**
- **Logged in:** navigation card grid — Incident Analyzer (3002), Supplier Directory (3003), Talent Tracker (3000), Backoffice Functions (3001), Public Website (3005)
- Protected cards: lock icon, `target="_blank"`, append `?token=<jwt>` when logged in
- Public website card/link: same tab, no token, no lock
- Logged-in hero: "Welcome, {name}", My Profile + Log Out
- Logged-out hero: Log In + Register
- On mount when token present: `GET /auth/me` to populate name; 401 clears token

**Verify:** Logged out → public content only, no tool URLs. Logged in → nav cards with token on protected links.

---

### Step 10 — Auth guards + API token wiring on all protected apps

**Goal:** Each internal tool redirects unauthenticated users to landing login; API calls include Bearer token.

**Per app** (copy identical `components/auth/auth-guard.tsx` + shared `lib/api.ts` pattern):

| App | Layout change | API change |
|-----|---------------|------------|
| `uis/backoffice/backoffice_functions/` | Client wrapper around `{children}` | N/A (no services/api calls) |
| `uis/incident_analyzer/` | AuthGuardLayout wrapper | Replace raw `fetch` with `apiFetch` + Bearer token |
| `uis/supplier_directory/` | AuthGuardLayout wrapper | Replace raw `fetch` with `apiFetch` + Bearer token |
| `apps/talent-pipeline-tracker/` | AuthGuardLayout wrapper | Wire HealthCore JWT into applicable API calls |

**Backend (same step or Step 10a):**

- Uncomment/enable `dependencies=[Depends(get_current_user)]` on `/suppliers` and `/incidents` routers in `app/api/v1/router.py`.
- Extend pytest — unauthenticated calls to suppliers/incidents return 401.

**Playwright (Step 10b or Step 13):**

- Add smoke tests in `uis/backoffice/landing/` for login, register, forgot-password → reset-password redirect.

**Pattern:** Create `components/auth/auth-guard-layout.tsx`:

```tsx
"use client";
import { AuthGuard } from "./auth-guard";
export function AuthGuardLayout({ children }: { children: React.ReactNode }) {
  return <AuthGuard>{children}</AuthGuard>;
}
```

Root `layout.tsx` imports wrapper; keeps `metadata` export server-side.

**Do NOT modify `uis/website/`.**

**Verify:** Direct visit to each app without token → redirect 3004/login; visit via landing card with token → loads.

---

### Step 11 — Website port fix

**Goal:** Resolve port 3000 conflict with talent tracker.

**Change:** `uis/website/package.json` → `"dev": "next dev --port 3005"`.

**Verify:** Website on 3005, no auth code added.

---

### Step 12 — Repository-wide favicon fix

**Goal:** Every Next.js app in the monorepo shows the HealthCore logo (navy square, white cross, cyan ring) in the browser tab. SVG-only or missing favicons fail in many browsers (including embedded IDE browsers) because `/favicon.ico` is not served.

**Canonical pattern** (already applied on `uis/backoffice/landing/`):

| File | Purpose |
|------|---------|
| `app/icon.tsx` | 32×32 PNG via `next/og` `ImageResponse` |
| `app/apple-icon.tsx` | 180×180 PNG for Apple touch |
| `next.config.ts` | Redirect `/favicon.ico` → `/icon` |

**Per app actions:**

| App | Port | Current state | Action |
|-----|------|---------------|--------|
| `uis/backoffice/landing/` | 3004 | **Done** — `icon.tsx` + `apple-icon.tsx` | Verify only; remove any leftover `app/icon.svg` |
| `uis/backoffice/backoffice_functions/` | 3001 | `app/icon.svg` + manual `icons` metadata | Replace with PNG pattern; remove `icon.svg`; drop `icons` from `layout.tsx` metadata |
| `uis/incident_analyzer/` | 3002 | No favicon | Add `icon.tsx`, `apple-icon.tsx`, redirect |
| `uis/supplier_directory/` | 3003 | No favicon | Add `icon.tsx`, `apple-icon.tsx`, redirect |
| `uis/website/` | 3005 | `app/icon.svg` + manual `icons` metadata | Replace with PNG pattern; remove `icon.svg`; drop `icons` from metadata |
| `apps/talent-pipeline-tracker/` | 3000 | `app/icon.svg` + manual `icons` metadata | Replace with PNG pattern; remove `icon.svg`; drop `icons` from metadata |

**Implementation notes:**

- Copy `app/icon.tsx` and `app/apple-icon.tsx` from `uis/backoffice/landing/` into each app (identical HealthCore logo artwork).
- Do **not** use `metadata.icons` pointing at `/icon.svg` — let Next.js auto-inject the generated PNG routes.
- Legacy static HTML apps (`apps/healthcore_web_portal/`, `apps/src/index.html`) are out of scope unless explicitly requested.

**Verify:** For each app, run `npm run verify`, restart dev server, hard-refresh tab (**Ctrl+Shift+R**). Confirm tab shows HealthCore logo and `curl -sI http://localhost:<port>/icon` returns `200` with `content-type: image/png`.

---

### Step 13 — Integration test + docs

**Manual checklist (from SPECS):**

1. Landing → register → welcome + nav cards.
2. Click Incident Analyzer → token accepted.
3. Profile → edit name → save.
4. Change password → logout.
5. Forgot password → reset → login with new password + success banner.
6. Public website on 3005 — no auth prompts.
7. Direct protected app access without token → login redirect.
8. HealthCore logo favicon visible on every Next.js app tab (Step 12).

**Docs updates:**

- `services/api/README.md` — reset endpoints, new env vars, link to this plan.
- Root `README.md` — landing app section, port table.
- `memory-bank/progress.md` — AUTH-02/03 delivered entry.
- `memory-bank/decisions.md` — email provider, URL token passing, guard pattern.

---

## File tree (target)

```
uis/backoffice/landing/
├── .env.local.example
├── app/
│   ├── globals.css
│   ├── layout.tsx
│   ├── (public)/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── login/page.tsx
│   │   ├── register/page.tsx
│   │   ├── forgot-password/page.tsx
│   │   └── reset-password/page.tsx
│   └── (protected)/
│       ├── layout.tsx
│       └── account/
│           ├── profile/page.tsx
│           └── change-password/page.tsx
├── components/
│   ├── auth/auth-guard.tsx
│   └── layout/{healthcore-logo,landing-header,landing-footer}.tsx
└── lib/api.ts

services/api/app/domains/auth/
├── router.py          (+ forgot-password, reset-password routes)
├── service.py         (+ reset helpers, email send)
├── schemas.py         (+ name, forgot/reset schemas)
└── token.py           (+ reset token encode/decode)

Each protected app:
└── components/auth/{auth-guard.tsx, auth-guard-layout.tsx}
```

---

## Risk register

| Risk | Mitigation |
|------|------------|
| URL token passing leaks JWT to history/logs | Accepted per SPECS; documented in HIPAA section for production |
| XSS + localStorage token theft | Accepted per SPECS; HttpOnly migration deferred |
| Talent tracker uses external API without HealthCore JWT | Guard protects page shell only; document limitation |
| `metadata` lost if root layout becomes `"use client"` | Use `AuthGuardLayout` client wrapper pattern |
| CORS misconfiguration blocks browser API calls | Update defaults + `.example.env`; document in README |
| Reset email not received in dev | Stdout fallback with full reset URL |
| Existing AUTH-01 tests break on schema changes | Extend tests in Step 2 before frontend depends on `name` |
| SVG favicon not visible in browser tabs | Step 12 — PNG `icon.tsx` + `favicon.ico` redirect on all Next.js apps |

---

## Clarifying questions — resolved

| # | Question | Answer |
|---|----------|--------|
| 1 | Email provider | **Resend** |
| 2 | `LOGIN_URL` | **Hardcoded** `http://localhost:3004/login` |
| 3 | API protection | **Protect `/suppliers` and `/incidents`** + add Bearer headers in frontends |
| 4 | Talent tracker | **Wire HealthCore JWT** into tracker API calls |
| 5 | Frontend tests | **Manual UAT + Playwright** smoke tests |

---

## References

- [AGENTS.md](../../../AGENTS.md) — session bootstrap, `.agents/` pre-build context, pre-commit workflow
- [SPECS_auth_2_3.md](SPECS_auth_2_3.md) — authoritative requirements for AUTH-02 and AUTH-03
- [SPECS_auth_1.md](SPECS_auth_1.md) — AUTH-01 backend baseline
- [IMPLEMENTATION_PLAN_auth_1.md](IMPLEMENTATION_PLAN_auth_1.md) — delivered AUTH-01 plan
- [evaluation_criteria.md](evaluation_criteria.md) — AUTH-01 eval checklist (extend for AUTH-02/03 separately if needed)
- Style reference: `uis/incident_analyzer/`
- Existing auth backend: `services/api/app/domains/auth/`
