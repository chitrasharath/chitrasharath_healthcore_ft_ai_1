# Talent Pipeline Tracker feature module

**Run via the landing app only** (`uis/backoffice/landing/` on port **3004**).

Routes: `/talent-tracker`, `/talent-tracker/candidates/*`. Relocated from `apps/talent-pipeline-tracker/`. Data API: `NEXT_PUBLIC_TRACKER_API_URL` (external tracker API; no HealthCore JWT).

The `node_modules` symlink points to `../landing/node_modules` for TypeScript resolution when imported by landing.
