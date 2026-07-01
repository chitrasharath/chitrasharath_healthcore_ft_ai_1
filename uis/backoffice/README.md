# HealthCore Backoffice

Internal backoffice umbrella folder for HealthCore Digital operational tools. All tools are served as **same-origin routes** on the landing app (`uis/backoffice/landing/`, port **3004**).

## Primary app — landing

```bash
cd uis/backoffice/landing
cp .env.local.example .env.local   # set NEXT_PUBLIC_API_URL, NEXT_PUBLIC_TRACKER_API_URL
npm install
npm run dev
```

Open **http://localhost:3004**. Requires the HealthCore API on port **8000** (`services/api`).

| Route | Module path | Description |
|-------|-------------|-------------|
| `/` | `landing/` | Hub — login, register, nav cards |
| `/incident-analyzer` | `uis/incident_analyzer/` | Patient incident CSV analysis |
| `/supplier-directory` | `uis/supplier_directory/` | Supplier registry |
| `/inventory` | `inventory/` | Medical supply stock, deliveries, consumption |
| `/talent-tracker` | `talent-tracker/` | Talent pipeline (external tracker API) |
| `/backoffice-functions` | `backoffice_functions/` | M2 utility manual test dashboard |
| `/account/profile` | `landing/` | User profile |
| `/account/change-password` | `landing/` | Change password |

Verify: `npm run verify` (lint + webpack build)

## Inventory module (`inventory/`)

Feature module for Milestone 5 medical supply inventory. Not a standalone Next.js app — components and API helpers are imported into landing via the `@backoffice/inventory` path alias.

```
uis/backoffice/inventory/
├── lib/           # inventory-api.ts, constants, format, timezones
├── hooks/         # products, orders, forms, timezone preference
├── components/    # tables, forms, landing, timezone bar
└── types/         # API TypeScript types
```

Landing routes: `landing/app/(protected)/inventory/`

| Route | UI |
|-------|-----|
| `/inventory` | Section landing (hero + nav cards) |
| `/inventory/products` | Supply list with stock indicators |
| `/inventory/orders/inbound` | Log vendor delivery |
| `/inventory/orders/outbound` | Log clinical consumption |
| `/inventory/orders` | Order history with timezone selector |

**Setup notes**

- API: `DATABASE_URL` in `services/api/.env` + `uv run seed` for Supabase inventory data.
- POST routes require login; GET products/orders are public on the API but UI routes are auth-guarded.
- For TypeScript in the inventory folder: `ln -sf ../landing/node_modules uis/backoffice/inventory/node_modules`

Plan: `memory-bank/references/milestone5_ai_plan/milestone5_frontend_implementation_plan.md`

## Other modules

| Module | Path | Notes |
|--------|------|-------|
| **Backoffice Functions** | [`backoffice_functions/`](backoffice_functions/) | M2 manual test dashboard (22 operations). Standalone dev on port 3001 is deprecated; use `/backoffice-functions` on landing. |
| **Talent Tracker** | [`talent-tracker/`](talent-tracker/) | Recruiting UI; data from `NEXT_PUBLIC_TRACKER_API_URL`. |
| **Shared** | [`shared/`](shared/) | `healthcoreFetch` — Bearer token injection for API calls. |

## Shared layout pattern

Protected tool routes use:

- `AuthGuard` from `landing/app/(protected)/layout.tsx`
- `ToolToolbar` (back to hub + logout) in per-tool `layout.tsx`
- Feature code in sibling folders, thin `page.tsx` files in landing

## Related docs

- Root README: backoffice overview, API endpoints, auth
- `services/api/README.md` — inventory API, Supabase, seed, pytest
- `memory-bank/progress.md` — milestone delivery status
