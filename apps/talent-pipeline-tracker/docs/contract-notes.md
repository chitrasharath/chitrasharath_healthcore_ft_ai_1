# API Contract Notes

This document maps expected API behavior for Talent Pipeline Tracker against the latest smoke-check execution.

## Source Inputs

- OpenAPI docs: https://playground.4geeks.com/tracker/api/v1/docs
- OpenAPI schema: https://playground.4geeks.com/tracker/api/v1/openapi.json
- Smoke report: ./api-smoke-check.md

## Endpoint Matrix

| Endpoint | Expected Use In App | Observed Smoke Result | Interpretation |
|---|---|---|---|
| GET /records | List candidates with filters/search/pagination | 200 | Route is reachable and usable. |
| GET /records/{id} | Candidate detail view | 200 | Route is reachable and usable. |
| POST /records | Create candidate | 422 with empty payload test | Reachable; validation works as expected for invalid payloads. |
| PATCH /records/{id} | Update status/stage fields | 404 with invalid id test | Reachable; production behavior depends on valid IDs. |
| PUT /records/{id} | Full-record correction path only | 422 with invalid payload/id test | Reachable; not used for create flow in current app behavior. |
| DELETE /records/{id} | Not in current product scope | 404 with invalid id test | Reachable but not currently wired in UI. |
| GET /records/{id}/notes | Read note timeline in edit flow | 200 | Route is reachable and usable. |
| POST /records/{id}/notes | Add note in edit flow | 404 with invalid id test | Reachable; production behavior depends on valid IDs. |
| DELETE /records/{id}/notes/{note_id} | Remove note in edit flow | 404 with invalid ids test | Reachable; production behavior depends on valid IDs. |

## Confirmed Decisions

- Candidate creation should use POST /records.
- PATCH is the update path used by the app for specific field updates.
- PUT remains a correction-oriented endpoint and is not used for candidate creation.
- Non-2xx smoke responses with intentionally invalid IDs still confirm endpoint reachability.

## Follow-Up Testing

1. Run mutation checks against real valid IDs in a controlled test dataset.
2. Record exact response payload shapes for PATCH and notes mutations.
3. Re-run smoke checks after backend schema or validation rule changes.
