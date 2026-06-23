from __future__ import annotations

import sys
from io import StringIO
from pathlib import Path

from app.domains.reporting.incidents.schemas import (
    BreakdownItem,
    IncidentAnalysisResponse,
    InvalidBreakdownItem,
    SatisfactionDistributionItem,
    SatisfactionResponse,
    TotalsResponse,
)
from app.domains.reporting.incidents.store import last_analysis_store


def _ensure_analysis_core_importable() -> None:
    repo_root = Path(__file__).resolve().parents[4].parent.parent
    analyzer_path = repo_root / "uis" / "incident_analyzer"
    path_str = str(analyzer_path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


def analyze_incidents_csv(content: bytes, filename: str) -> IncidentAnalysisResponse:
    _ensure_analysis_core_importable()
    from analysis_core import analyze, load_incidents, to_export_rows

    if not content:
        raise ValueError("Uploaded file is empty.")

    if not filename.lower().endswith(".csv"):
        raise ValueError("Invalid file format. Upload a CSV file.")

    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("File is not valid UTF-8 text.") from exc

    buffer = StringIO(text)
    df = load_incidents(buffer)
    result = analyze(df, filename)

    response = IncidentAnalysisResponse(
        source_filename=result.source_filename,
        analyzed_at=result.analyzed_at,
        totals=TotalsResponse(
            total=result.totals.total,
            valid=result.totals.valid,
            invalid=result.totals.invalid,
        ),
        invalid_breakdown=[
            InvalidBreakdownItem(rule=item.rule, label=item.label, count=item.count)
            for item in result.invalid_breakdown
        ],
        by_category=[
            BreakdownItem(label=item.label, count=item.count, percentage=item.percentage)
            for item in result.by_category
        ],
        by_status=[
            BreakdownItem(label=item.label, count=item.count, percentage=item.percentage)
            for item in result.by_status
        ],
        by_country=[
            BreakdownItem(label=item.label, count=item.count, percentage=item.percentage)
            for item in result.by_country
        ],
        satisfaction=SatisfactionResponse(
            scored_cases=result.satisfaction.scored_cases,
            total_closed=result.satisfaction.total_closed,
            average=result.satisfaction.average,
            max_score=result.satisfaction.max_score,
            distribution=[
                SatisfactionDistributionItem(
                    score=item.score,
                    label=item.label,
                    count=item.count,
                )
                for item in result.satisfaction.distribution
            ],
        ),
    )

    export_rows = to_export_rows(result)
    last_analysis_store.save(response, export_rows)
    return response
