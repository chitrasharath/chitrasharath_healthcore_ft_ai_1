# ✅ What We Will Evaluate

- [ ] The main flow in `data/pipelines/pipeline.py` invokes at least three subflows (`@flow`) instead of containing all logic directly.
- [ ] Each subflow has explicit inputs and outputs and can be executed independently.
- [ ] The file `tests/pipelines/test_pipeline.py` exists and contains at least three unit tests for transformation tasks.
- [ ] At least one test verifies the defensive behaviour of a task against invalid input.
- [ ] At least one test validates a KPI's computed value against its definition in `CONTEXT-company.md`.
- [ ] `python -m pytest tests/pipelines/test_pipeline.py` passes without errors.
- [ ] `python data/pipelines/pipeline.py` runs the full ETL flow without errors.
- [ ] The run command is documented in `data/pipelines/PIPELINE_DESIGN.md` or inline comments.
- [ ] Subflow names, task names, and test names reflect the domain vocabulary and KPI names from `CONTEXT-company.md`.
- [ ] `telemetry_events` and `services/telemetry/analysis.py` remain unmodified throughout the refactor.
- [ ] A dashboard exists in `uis/backoffice/` that displays every KPI from `CONTEXT-company.md`'s "KPIs to Measure" section, correctly labeled, sourced from your `services/reporting/` endpoint.
- [ ] The dashboard is legible to a non-technical business stakeholder, not just to another engineer.
