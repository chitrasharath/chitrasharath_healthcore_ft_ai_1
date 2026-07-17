# `scripts` folder

This folder contains **helper scripts** for the monorepo: development automation, maintenance utilities, repetitive tasks (setup, lint, migrations, data generation, etc.), and internal tooling.

- **Main purpose**: group support tools that do not belong to a specific app, agent, or pipeline but make the team’s work easier.
- **Recommendation**: document each script (what it does, parameters, requirements, usage examples) and keep them reproducible (and safe) across environments.

## Docker purge

Stop Compose and reclaim disk (anonymous volumes, build cache, unused images):

```bash
./scripts/docker_purge.sh
./scripts/docker_purge.sh --soft   # down -v only
```

## Telemetry index verification

After Phase 3 storage is deployed and the API has started with `DATABASE_URL` set:

```bash
# From repo root (reads services/api/.env)
uv run python scripts/verify_telemetry_indexes.py
```

Checks: `tags` is `jsonb`, btree + GIN indexes exist, and a forced `EXPLAIN` uses `idx_telemetry_events_tags`.

For manual inspection in Supabase SQL Editor, run `scripts/verify_telemetry_indexes.sql`.

> _Spanish version: [README.es.md](./README.es.md)._
