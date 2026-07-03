# Incident Analyzer feature module

HealthCore patient incident CSV analysis with HIPAA-safe aggregate reporting. Shared logic lives in `analysis_core.py`; the CLI, FastAPI backend, and Next.js dashboard all use the same calculations.

## Dashboard (via landing)

**Run via the landing app only** (`uis/backoffice/landing/` on port **3001**).

Route: `/incident-analyzer`. Set `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1` in `uis/backoffice/landing/.env.local`.

The standalone Next.js app on port 3002 is deprecated.

## CLI script

From `uis/incident_analyzer/`:

```bash
uv sync
uv run analyze incidents-healthcore.csv
```

The script prints a summary to the console and prompts `Export results to CSV? [y / n]:`. Answer `y` to write `incident-analysis-export.csv` in the current directory.

## Backend

Incident analysis API routes are on `services/api` under `/api/v1/incidents/analyze` and `/api/v1/incidents/results/export`. See [services/api/README.md](../../services/api/README.md).

## Related docs

- [uis/backoffice/README.md](../backoffice/README.md) — landing routes and setup
- [memory-bank/progress.md](../../memory-bank/progress.md) — delivery status
