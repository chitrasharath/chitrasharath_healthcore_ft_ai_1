# Central Incident Manager — Evaluation Criteria

## ✅ What We Will Evaluate

### 🔗 Model and seed

- [ ] The model includes all required fields with their integrity constraints.
- [ ] The seed script correctly loads historical incidents assigning `origin: "customer"`.
- [ ] Invalid CSV records are not inserted and are reported to the console.
- [ ] The script is idempotent: running it twice does not duplicate data.

### Backend

- [ ] All endpoints respond with the correct HTTP codes for both happy path and error cases.
- [ ] Validation errors identify the problematic field in the JSON response.
- [ ] No endpoint exposes a stack trace to the client.
- [ ] Invalid status transitions are rejected with `400`.
- [ ] The `/summary` endpoint returns correct metrics even when there are no incidents.

### Frontend

- [ ] The form validates required fields on the client before submitting.
- [ ] Loading states are visible and the submit button is disabled during the request.
- [ ] API errors are shown in plain language to the user, never as technical text.
- [ ] The list correctly handles all three possible states: loading, empty, with data.
- [ ] Status updates in the list revert visually if the request fails.
- [ ] The summary panel does not break the page if its request fails.

### Cross-cutting

- [ ] The validation logic from the previous project is extracted into `packages/shared/` and reused by both the script and the API, without duplication.
- [ ] Code is organised according to the monorepo folder structure (`scripts/`, `services/`, `uis/`, `packages/shared/`).

---

## 📦 How to Submit This Project

The project must be organised in the monorepo as follows:

```
scripts/
  seed_incidents.py       ← historical CSV load script

packages/
  shared/                 ← validation logic shared between script and API

services/
  <api-service-name>/     ← backend with management and summary endpoints

uis/
  <ui-name>/               ← registration, list, and summary interface
```
