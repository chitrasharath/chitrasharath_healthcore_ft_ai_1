## What We Will Evaluate

- [ ] The file `data/pipelines/pipeline.py` exists and defines at least one flow with three or more tasks.
- [ ] At least one task has `retries` configured with a value greater than zero and a comment justifying the number chosen.
- [ ] At least one optional task is invoked with `return_state=True` and the flow continues executing when that task fails.
- [ ] At least one transformation task has caching configured with `cache_key_fn` and `cache_expiration`.
- [ ] The load phase is idempotent: running the pipeline twice over the same data does not produce duplicates in the database.
- [ ] Each pipeline run records at least five metadata fields (start time, end time, records processed, status, errors) in the database or in a structured log file.
- [ ] `python data/pipelines/pipeline.py` runs the full ETL flow without errors.
- [ ] The run command is documented in `data/pipelines/PIPELINE_DESIGN.md` or inline comments.
- [ ] At least one endpoint exists in `services/` that returns the metadata of the last pipeline run (status, start time, end time, records processed).
- [ ] At least one endpoint exists in `services/` that triggers a manual flow run, importing the function from `data/pipelines/` without duplicating the logic.
- [ ] The implemented design is consistent with `data/pipelines/PIPELINE_DESIGN.md` — the stages, entities, and resilience strategies described there are reflected in the code.
