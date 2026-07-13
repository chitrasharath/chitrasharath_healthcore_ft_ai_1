-- Verify telemetry_events indexes (run in Supabase SQL Editor).
-- Prerequisite: API has started at least once with DATABASE_URL set so
-- ensure_telemetry_indexes() created indexes on startup.

-- 1) Column type must be jsonb (GIN requires jsonb, not json)
SELECT column_name, data_type, udt_name
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'telemetry_events'
  AND column_name = 'tags';

-- 2) All three indexes should exist
SELECT indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename = 'telemetry_events'
ORDER BY indexname;

-- 3) GIN index plan — containment query (@>)
-- On small tables Postgres may Seq Scan; use step 4 to force GIN for sanity check.
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, event_type, tags
FROM telemetry_events
WHERE tags @> '{"schemaVersion": "1.1.0"}'::jsonb;

-- 4) Force GIN usage (session only; for index sanity check)
SET enable_seqscan = off;

EXPLAIN (ANALYZE, BUFFERS)
SELECT id, event_type, tags
FROM telemetry_events
WHERE tags @> '{"schemaVersion": "1.1.0"}'::jsonb;

RESET enable_seqscan;

-- 5) Sample tag filter (adjust keys to match your seeded data)
SELECT event_type, tags->>'jurisdiction' AS jurisdiction, tags
FROM telemetry_events
WHERE tags ? 'jurisdiction'
ORDER BY timestamp DESC
LIMIT 10;
