## What We Will Evaluate

- [ ] The file `data/pipelines/PIPELINE_DESIGN.md` exists in the monorepo and is written in readable Markdown.
- [ ] The pipeline purpose is defined in a single concrete sentence that mentions the company's business, not only the technology.
- [ ] The data flow diagram shows at least three distinct stages (extraction, transformation, load) with the real entity or table names from the company.
- [ ] The strategy for handling updates to existing records is documented with a concrete mechanism (e.g., upsert by primary key, last-modified timestamp, control table).
- [ ] The idempotency strategy is explicit: it describes what happens on the second run after a load-phase failure, not just what would be desirable.
- [ ] The execution log specifies at least five fields with the field name, data type, and justification for why that field is necessary for auditing.
- [ ] The Prefect mapping identifies at least two flows and three tasks with concrete names aligned with the pipeline stages.
- [ ] The design is consistent with the telemetry events and KPIs defined in the `CONTEXT-company.md`.
