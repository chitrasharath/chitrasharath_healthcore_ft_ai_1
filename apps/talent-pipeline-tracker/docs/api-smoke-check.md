# API Smoke Check

- Executed at: 2026-05-18T22:34:00.502Z
- Base URL: https://playground.4geeks.com/tracker/api/v1
- Strategy: mutating endpoints tested with invalid IDs or invalid payloads to confirm reachability without updating real records.

| Endpoint | Method | Status | Reachable | Note |
|---|---|---:|---|---|
| GET /records | GET | 200 | yes | ok |
| GET /records/{id} | GET | 200 | yes | ok |
| POST /records | POST | 422 | yes | non-2xx but reachable |
| PUT /records/{id} | PUT | 422 | yes | non-2xx but reachable |
| PATCH /records/{id} | PATCH | 404 | yes | non-2xx but reachable |
| DELETE /records/{id} | DELETE | 404 | yes | non-2xx but reachable |
| GET /records/{id}/notes | GET | 200 | yes | ok |
| POST /records/{id}/notes | POST | 404 | yes | non-2xx but reachable |
| DELETE /records/{id}/notes/{note_id} | DELETE | 404 | yes | non-2xx but reachable |

## Mismatch Notes
- POST /records with empty payload is expected to fail validation; a non-2xx response here still confirms route reachability.
- PATCH and PUT were checked with invalid IDs to avoid side effects.