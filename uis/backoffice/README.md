# HealthCore Backoffice

Internal backoffice umbrella folder for HealthCore Digital operational tools.

## Apps

| App | Path | Description |
|-----|------|-------------|
| **Backoffice Functions** | [`backoffice_functions/`](backoffice_functions/) | M2 utility manual test dashboard (22 operations) |

Additional internal apps may be added as sibling folders under `uis/backoffice/`.

## Run Backoffice Functions

```bash
cd uis/backoffice/backoffice_functions
npm install
npm run dev
```

Open **http://localhost:3001** (webpack dev server).

Verify: `npm run verify`
