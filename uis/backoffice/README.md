# HealthCore Backoffice

Internal backoffice umbrella folder for HealthCore Digital operational tools. All tools are served as **same-origin routes** on the landing app (`uis/backoffice/landing/`, port **3001**).

## Primary app — landing

All internal tools are same-origin routes on this app. **Only landing** needs `.example.env` → `.env.local` for manual dev; aliased modules inherit its env vars.

```bash
cd uis/backoffice/landing
cp .example.env .env.local   # NEXT_PUBLIC_API_URL, NEXT_PUBLIC_TRACKER_API_URL
npm install
npm run dev
```

Open **http://localhost:3001**. Requires the HealthCore API on port **8000** (`services/api`).

| Route | Module path | Description |
|-------|-------------|-------------|
| `/` | `landing/` | Hub — login, register, nav cards |
| `/incident-analyzer` | `uis/incident_analyzer/` | Patient incident CSV analysis |
| `/supplier-directory` | `uis/supplier_directory/` | Supplier registry |
| `/inventory` | `inventory/` | Medical supply stock, deliveries, consumption |
| `/incident-manager` | `incident-manager/` | Patient incident CRUD and summary dashboard |
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

## Incident manager module (`incident-manager/`)

Feature module for centralized patient incident logging and tracking. Imported into landing via the `@backoffice/incident-manager` path alias.

Landing routes: `landing/app/(protected)/incident-manager/`

| Route | UI |
|-------|-----|
| `/incident-manager` | Section landing (hero + nav cards) |
| `/incident-manager/new` | Create incident form |
| `/incident-manager/list` | Filterable incident list |
| `/incident-manager/summary` | Summary dashboard |
| `/incident-manager/{id}` | Incident detail |
| `/incident-manager/{id}/edit` | Edit incident |

**Setup notes**

- API: `DATABASE_URL` in `services/api/.env` required for incident CRUD routes.
- Seed (optional): `docker compose exec api uv run python /app/scripts/seed_incidents.py` or run `scripts/seed_incidents.py` locally with API env configured.

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

- [README.md](../../README.md) — Docker quick start, manual development, doc map
- [services/api/README.md](../../services/api/README.md) — API setup, endpoints, pytest
- [memory-bank/progress.md](../../memory-bank/progress.md) — milestone delivery status
