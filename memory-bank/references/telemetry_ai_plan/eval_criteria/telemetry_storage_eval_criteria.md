# ✅ What We Will Evaluate

- [ ] The `telemetry_events` table exists in Supabase with the eight columns, the three indexes, and no UPDATE/DELETE logic
- [ ] The `POST /telemetry/events` endpoint does bulk insert and returns `{ "received", "stored", "rejected" }`
- [ ] Invalid events are rejected individually without cancelling the batch — valid ones are persisted (per-event `model_validate`, not a typed `list[TelemetryEvent]` body that would return `422` for the whole batch)
- [ ] The `TelemetryEvent` Pydantic model has not been modified from the previous project — it is reused as-is
- [ ] The frontend has not changed a single line — the stub → real substitution is completely transparent
- [ ] Events appear in `telemetry_events` with `event_type`, `timestamp`, and `tags` correctly populated
- [ ] Stored `tags` JSON preserves the property allowlists and CONTEXT-specific dimensions documented in the student's `telemetry-plan.md`
- [ ] The insert is a single operation per batch, not one INSERT per event
