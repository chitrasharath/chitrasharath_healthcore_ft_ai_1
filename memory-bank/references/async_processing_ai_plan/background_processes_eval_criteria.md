# ✅ What We Will Evaluate

- [ ] The script is an independent process: it does not import or execute FastAPI code on the application's main thread.
- [ ] The `pending → processing → completed | failed` state machine is implemented and `job_runs` records reflect the actual status of each execution, including `target_date`.
- [ ] The `processing` status acts as the distributed lock (no separate lock mechanism): demonstrable by launching two instances of the script simultaneously.
- [ ] The script is idempotent per `target_date`: running it twice for the same day produces the same result as running it once, without duplicating CSV files or pipeline executions.
- [ ] No record remains in `processing` status after a failure: the `try/except/finally` block guarantees the transition to `failed`.
- [ ] The CSV output exists in `data/raw/` with the correct name and contains telemetry data exported from `telemetry_events` for the target date (backup only — pipeline reads from DB).
- [ ] `job_runs` and `pipeline_runs` coexist without duplication of responsibilities.
- [ ] Logs include timestamp, job name, and status on every relevant event.
- [ ] The trigger is configured and the cron expression documented in the PR.
- [ ] `TARGET_DATE` allows the script to run on arbitrary dates without modifying the code.
