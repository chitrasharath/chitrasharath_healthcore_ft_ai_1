# Telemetry — Phase 2 (Frontend Capture + Stub Endpoint) — Build Spec

> Instructions for a coding agent. Reconciles `telemetry_frontend_screenshot.md`,
> `telemetry_frontend_readme.md`, and `telemetry_frontend_context.md` against the codebase.
> Where the docs cite paths/entities that don't exist, the codebase wins. Implements the
> event catalog and envelope defined in `telemetry_design_specs.md`.

---

## 1. Overview

Two deliverables:
1. A **stub** `POST /api/v1/telemetry/events` endpoint in the FastAPI backend that validates format and
   returns `{ "received": N }` — **no persistence** (that is Phase 3 / `telemetry_storage_specs.md`).
2. A frontend **`TelemetryService`** with a single `track()` entry point (local queue → batch → `sendBeacon` →
   retry), plus instrumentation of the inventory and auth flows.

## 2. Tech stack / ground truth (differs from the docs — use these)

- Backend: FastAPI, `services/api/`, all routes under `/api/v1`. Routers live in
  `app/domains/<domain>/router.py` and are wired in `app/api/v1/router.py`. Runs on **:8000**.
- Config: `app/core/config.py` (`pydantic-settings`, reads `.env`).
- Frontend **host app**: `uis/backoffice/landing` (Next.js, `next dev --webpack --port 3001`). It hosts the
  `inventory` module via the `@backoffice/inventory/*` alias and shares `@backoffice/shared/*`.
- Frontend API client: `uis/backoffice/shared/lib/healthcore-api.ts` (`healthcoreFetch`), base URL
  `NEXT_PUBLIC_API_URL` (default `http://localhost:8000/api/v1`). Auth = JWT in `localStorage["token"]`.
- **The doc path `uis/backoffice/src/services/telemetry.ts` does not exist.** Put the service in
  **`uis/backoffice/shared/lib/telemetry.ts`** so both `landing` (auth) and `inventory` can import it via `@backoffice/shared/lib/telemetry`.

## 3. Phase 2a — Backend stub endpoint

Create a new telemetry domain: `services/api/app/domains/telemetry/`.

- `schemas.py` — Pydantic models (this model is **reused unchanged in Phase 3**, so define it correctly now):

  ```python
  from pydantic import BaseModel
  from datetime import datetime
  from typing import Any

  class TelemetryEvent(BaseModel):
      eventId: str
      timestamp: datetime          # ISO 8601
      sessionId: str
      userId: str
      event_type: str
      schemaVersion: str
      requestId: str
      service: str                 # constant "backoffice"
      properties: dict[str, Any] = {}

  class TelemetryBatch(BaseModel):
      events: list[dict[str, Any]]  # loose per-item dicts — do NOT type as list[TelemetryEvent]
  ```

  > The batch is intentionally loose (`list[dict]`) so Phase 3 can validate per-event and support partial
  > acceptance. In the stub you may still `model_validate` each item to log `event_type`, but do not make the
  > whole request fail if one item is malformed.

- `router.py` — `router = APIRouter(prefix="/telemetry", tags=["telemetry"])` with
  `POST /events`. Wire it in `app/api/v1/router.py` **without** a `get_current_user` dependency (like the
  `inventory`/`auth` routers, not the `incidents`/`suppliers` routers). Final path: `/api/v1/telemetry/events`.
  The stub must:
  - Accept `{ "events": [...] }`.
  - Log the received count and each item's `event_type`.
  - Return `200` with `{ "received": <len(events)> }`.
  - **Not** touch any database.

  > **No JWT auth on this endpoint (deliberate).** `navigator.sendBeacon` (used for the tab-close flush) cannot
  > set an `Authorization` header, so requiring a Bearer token would silently drop the most important batch —
  > the one sent as the user leaves. Telemetry is a fire-and-forget ingestion sink: identity travels inside the
  > envelope (`userId`, `sessionId`), the endpoint is protected by the existing CORS origin allowlist
  > (`settings.cors_origin_list`) + strict per-event validation (Phase 3), and rows are treated as untrusted.
  > `userId` is therefore self-reported (not header-authenticated) — acceptable because events are non-critical
  > and contain no PII. Optionally add lightweight rate limiting.
- Config: add `telemetry_endpoint: str = ""` to `Settings` in `app/core/config.py` and add
  `TELEMETRY_ENDPOINT` to `.example.env` (establish the pattern even though the stub doesn't route with it).

## 4. Phase 2b — `TelemetryService` (`uis/backoffice/shared/lib/telemetry.ts`)

Single module owning **all** telemetry network I/O. Constants:

```ts
const SCHEMA_VERSION = "1.0.0";
const SERVICE = "backoffice";
const FLUSH_INTERVAL_MS = 10_000;   // 10s
const MAX_QUEUE_SIZE = 20;          // flush when reached
const MAX_RETRIES = 3;              // then discard batch
```

Responsibilities:

- **Local queue:** in-memory array of enriched events.
- **Batch + debounce:** flush every 10s OR when the queue hits 20 events, whichever first. Send one POST with
  body `{ "events": [...] }` to `process.env.NEXT_PUBLIC_TELEMETRY_ENDPOINT`. **No hardcoded URL.**
- **Transport (do NOT use `healthcoreFetch`):** use a standalone `fetch` for the interval/size flush and
  `navigator.sendBeacon` for the tab-close flush. The telemetry endpoint is unauthenticated (§3), so send **no**
  `Authorization` header — this keeps the `fetch` path and the `sendBeacon` path identical (beacon cannot set
  headers). Never route telemetry through `shared/lib/healthcore-api.ts`: it attaches the Bearer token and
  redirects to `/login` on 401, which must never be triggered by a telemetry call.
- **Auto-enrichment:** `track()` adds `eventId` (`crypto.randomUUID()`), `timestamp` (ISO 8601, capture time),
  `sessionId`, `userId`, `schemaVersion`, `requestId` (`crypto.randomUUID()` per event/batch for correlation),
  and `service`. Callers pass only `eventType` + `properties`.
- **`sessionId`:** generated once at login as a UUID and stored in `sessionStorage` (there is no session id
  today). Read it in the service; regenerate on a fresh login.
- **`userId`:** the backend has no user id in the token payload accessible client-side beyond the JWT — resolve
  it via the existing `GET /api/v1/auth/me` (returns the user) once after login and cache it for the session.
  If unavailable, fall back to `""` (do not block).
- **Reliable flush:** on `document` `visibilitychange` → `hidden`, send the pending batch with
  `navigator.sendBeacon(endpoint, blob)`.
- **Retry with backoff:** on network failure, retry up to 3 times with exponential backoff, then discard the
  batch silently (telemetry must never block the app).
- **Public API:** `export function track(eventType: string, properties: Record<string, unknown>): void`.
  `eventType` becomes the envelope `event_type`. Nothing else is public.

## 5. Phase 2c — Inventory instrumentation

Instrument via `track()` at the real call sites (no direct `fetch`/`axios` for telemetry anywhere outside
`telemetry.ts`). `jurisdiction` is **derived on the client** from the selected supply's `country`
(`US`→`us`, `UK`→`uk`); the products loaded via `listProducts()` (`MedicalSupplyRead`) include `country`.

| `event_type` | Where | Properties (allowlist only) |
| --- | --- | --- |
| `supply_delivery_created` | `inventory/hooks/use-inbound-form.ts` after `createInboundOrder` resolves | `supply_id`, `quantity`, `clinic_id`, `jurisdiction` |
| `supply_consumption_created` | `inventory/hooks/use-outbound-form.ts` after `createOutboundOrder` resolves | `supply_id`, `quantity`, `consumption_type`, `clinic_id`, `jurisdiction` |
| `supply_consumption_failed` | outbound form catch block (400 insufficient stock / validation) | `error_code`, `supply_id`, `clinic_id`, `jurisdiction` |
| `supply_list_viewed` | `inventory/hooks/use-products.ts` (or products table mount) | `item_count` |
| `orders_list_viewed` | `inventory/hooks/use-orders.ts` (orders table mount) | `item_count` |

> **`product_created` is intentionally NOT instrumented in Phase 2.** `POST /inventory/products` exists on the
> backend but has **no UI surface** in the backoffice — `inventory/lib/inventory-api.ts` exposes only
> `listProducts`/`getProduct` (GET) and the two order POSTs; there is no `createProduct` call or create-product
> form. Phase 2 captures exclusively at frontend `track()` call sites, so an API-only endpoint has nowhere to be
> instrumented, and emitting it from the backend would violate the single-`track()` / no-backend-emitted-telemetry
> rule. The five inventory events above still satisfy the ≥5 minimum. If a create-product UI is added later,
> instrument `product_created` in that form's success handler with `supply_id`, `category`, `jurisdiction`.

Rules:
- **Only** allowlist properties per event — no extras "just in case".
- `consumption_type` must be the exact value submitted in the form (`clinical_use` | `expiry_waste`) — never inferred.
- `clinic_id` is the existing integer from the form fields.
- `error_code` for `supply_consumption_failed`: derive from the API error (e.g. `INSUFFICIENT_STOCK` for the 400
  insufficient-stock path); do not include the raw error message if it could contain PII.

## 6. Phase 2d — Auth instrumentation (host app `landing`)

Instrument in the auth hooks, not per page:

| `event_type` | Where | Properties |
| --- | --- | --- |
| `user_login_succeeded` | `landing/hooks/use-login-form.ts` after 200; also generate the `sessionId` here | `jurisdiction` if known, else omit |
| `user_login_failed` | `use-login-form.ts` failure branch | `reason`: `invalid_credentials` (401) \| `network_error` (thrown) |
| `session_expired` | `shared/lib/healthcore-api.ts` where a 401 triggers the `/login` redirect | *(envelope only)* — may set `reason: session_expired` on a `user_login_failed` if the design plan models it that way |

**Never** put the entered email/password anywhere in properties.

## 7. Environment configuration

- Frontend: add `NEXT_PUBLIC_TELEMETRY_ENDPOINT=http://localhost:8000/api/v1/telemetry/events` to
  `uis/backoffice/landing/.env.local` and document it in the app's example env.
- Backend: `TELEMETRY_ENDPOINT` in `.example.env` and `Settings` (§3).
- Note the corrected path: `/api/v1/telemetry/events` (the docs' `/telemetry/events` omits the `/api/v1` prefix).

## 8. Dependencies & workflow

- Backend: no new packages (FastAPI + pydantic already present; managed with **uv** — `uv sync` / `uv run` in `services/api/`).
- Frontend: no new packages (`crypto.randomUUID`, `navigator.sendBeacon` are built-ins).
- Run backend on :8000, `landing` on :3001. Verify in DevTools Network that batches (not per-click requests)
  POST to `/api/v1/telemetry/events` and return `200 { "received": N }`; confirm backend logs list the event types.
- PR: title `[W16D47] Telemetry Frontend`; description lists event→hook mapping, a DevTools screenshot of a
  batched 200 response, and whether the auth activity was implemented.

## 9. Definition of done (maps to `telemetry_frontend_eval_criteria.md`)

- [ ] `POST /api/v1/telemetry/events` stub returns `{ "received": N }`, no DB writes.
- [ ] `TelemetryEvent` Pydantic model matches the envelope (incl. `requestId` **and** `service`); reusable in Phase 3.
- [ ] `TELEMETRY_ENDPOINT` (backend) + `NEXT_PUBLIC_TELEMETRY_ENDPOINT` (frontend) established; no hardcoded URL.
- [ ] `TelemetryService`: queue + 10s/20-event batch + `sendBeacon` on `visibilitychange` + retry w/ backoff.
- [ ] `track()` auto-fills `eventId`, `sessionId`, `userId`, `timestamp`, `schemaVersion`, `requestId`, `service`.
- [ ] Single `track()` entry point; zero direct `fetch`/`axios` telemetry calls elsewhere (grep the backoffice).
- [ ] Inventory + auth events instrumented with allowlist-only properties; `jurisdiction` derived from supply `country`.
- [ ] No PII (email/name/password) in any event.
- [ ] DevTools shows batched 200 responses.
