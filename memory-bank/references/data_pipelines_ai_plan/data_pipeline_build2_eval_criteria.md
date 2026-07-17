## What We Will Evaluate

- [ ] The main flow in `data/pipelines/pipeline.py` invokes at least three subflows (`@flow`) instead of containing all logic directly.
- [ ] Each subflow has explicit inputs and outputs and can be executed independently.
- [ ] The file `tests/pipelines/test_pipeline.py` exists and contains at least three unit tests for transformation tasks.
- [ ] At least one test verifies the defensive behaviour of a task against invalid input.
- [ ] `python -m pytest tests/pipelines/test_pipeline.py` passes without errors.
- [ ] `python data/pipelines/pipeline.py` runs the full ETL flow without errors.
- [ ] The run command is documented in `data/pipelines/PIPELINE_DESIGN.md` or inline comments.
- [ ] Subflow names, task names, and test names reflect the domain vocabulary from `data/pipelines/PIPELINE_DESIGN.md`.
