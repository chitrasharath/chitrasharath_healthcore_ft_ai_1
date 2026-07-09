# ✅ What We Will Evaluate

- [ ] The stub `POST /telemetry/events` endpoint exists, accepts arrays with the `TelemetryEvent` model, and returns `{ "received": N }`
- [ ] The Pydantic model `TelemetryEvent` reflects the standard envelope from the Phase 1 plan with all its fields
- [ ] The endpoint URL is read from `NEXT_PUBLIC_TELEMETRY_ENDPOINT` — it is not hardcoded
- [ ] The backend declares `TELEMETRY_ENDPOINT` in its environment configuration to establish the pattern from the start
- [ ] The `TelemetryService` implements local queue, batch+debounce (10s / 20 events), flush with `sendBeacon`, and retry with backoff
- [ ] The service generates `eventId`, `sessionId`, `userId`, `timestamp`, `schemaVersion`, and `requestId` automatically — the component calling `track()` does not pass them manually
- [ ] There are no direct `fetch` / `axios` calls for telemetry outside the `TelemetryService`
- [ ] Inventory flow events are instrumented respecting the allowlist of properties for each event
- [ ] Failed order attempts (validation error or insufficient stock) are tracked from the catch blocks
- [ ] Product/stock list viewed is tracked when the products page loads
- [ ] There is no PII (email, name, password) in any event sent
- [ ] The DevTools Network tab shows batches arriving at the endpoint with the correct format and a 200 response
