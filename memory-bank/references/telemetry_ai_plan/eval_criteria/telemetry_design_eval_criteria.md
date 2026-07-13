# ✅ What We Will Evaluate — Telemetry Design Plan

- [ ] The 3 KPIs identified are representative of the assigned company's business and are justified with data from `CONTEXT-company.md`.
- [ ] Every event has a hypothesis and a business decision that justifies it — no "just in case" events.
- [ ] The Event Envelope is consistent across all events and contains at least: `eventId`, `timestamp` (ISO 8601), `sessionId`, `userId`, `event_type` in `entity_action` format, `schemaVersion`, `requestId`, and `properties`.
- [ ] Every event has a documented **property allowlist** — only explicitly permitted keys.
- [ ] The `event-schemas.json` file is valid and the schemas are consistent with the Markdown plan.
- [ ] The stream/batch decision is justified by business urgency, not technical preference.
- [ ] Sensitive data or PII is identified and documented with its anonymisation or sanitisation strategy.
- [ ] The risks and exclusions section demonstrates critical thinking: events were discarded for a reason.
- [ ] The plan is precise enough for another developer to instrument it without needing clarification.
