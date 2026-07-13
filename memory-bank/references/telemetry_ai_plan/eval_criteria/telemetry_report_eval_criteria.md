# ✅ What We Will Evaluate

- [ ] The file `services/telemetry/analysis.py` exists and contains at least two independent metric functions
- [ ] Each function follows the formula `load (SQL) → refine (Pandas) → convert types → group → aggregate` in that order
- [ ] Timestamps are converted to `datetime` with `utc=True` before any temporal `groupby()`
- [ ] No loops are used to calculate metrics — only Pandas operations
- [ ] Each function returns a list of dicts serialisable to JSON
- [ ] The `GET /telemetry/report` endpoint accepts optional `start_date` and `end_date` and defaults to 7 days
- [ ] The endpoint returns JSON with the structure `{ "period": {...}, "metrics": {...} }`
- [ ] The endpoint has an in-memory cache with a 60-second TTL — it does not recalculate on every request
- [ ] Each metric answers a KPI from the student's `telemetry-plan.md`, justified with data from `CONTEXT-company.md`
- [ ] The returned metrics have a grouping dimension — they are not global numbers without context
