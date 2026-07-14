# `data/pipelines` folder

Telemetry KPI ETL lives here, split by stage:

| Path | Role |
|------|------|
| `pipeline.py` | Prefect flow orchestrator + CLI entry (`uv run python data/pipelines/pipeline.py`) |
| `config.py` | Watermark / event-type / version constants |
| `extract/` | Watermark window, `extract_telemetry_events` task, PHI / quarantine scans |
| `transform/` | `transform_kpi_aggregates` task (`build_metrics`) |
| `load/` | Upserts + report readers (`repository.py`), run-log helpers, load + snapshot tasks |

Design: [`docs/data_pipelines/pipeline-design.md`](../../docs/data_pipelines/pipeline-design.md).

> _Spanish version: [README.es.md](./README.es.md)._
