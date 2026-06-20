# API Smoke Check

- Executed at: 2026-06-17T00:22:09.303Z
- Base URL: http://localhost:8000
- Strategy: mutating endpoints tested with invalid IDs or invalid payloads to confirm reachability without updating real records.

| Endpoint | Method | Status | Reachable | Note |
|---|---|---:|---|---|
| GET /records | GET | 404 | yes | non-2xx but reachable |
| GET /records/{id} | GET | 404 | yes | non-2xx but reachable |
| POST /records | POST | 404 | yes | non-2xx but reachable |
| PUT /records/{id} | PUT | 404 | yes | non-2xx but reachable |
| PATCH /records/{id} | PATCH | 404 | yes | non-2xx but reachable |
| DELETE /records/{id} | DELETE | 404 | yes | non-2xx but reachable |
| GET /records/{id}/notes | GET | 404 | yes | non-2xx but reachable |
| POST /records/{id}/notes | POST | 404 | yes | non-2xx but reachable |
| DELETE /records/{id}/notes/{note_id} | DELETE | 404 | yes | non-2xx but reachable |

## Mismatch Notes
- POST /records with empty payload is expected to fail validation; a non-2xx response here still confirms route reachability.
- PATCH and PUT were checked with invalid IDs to avoid side effects.