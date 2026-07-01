"""Shared incident analysis logic for CLI and API."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import BinaryIO, TextIO, Union

import pandas as pd
from healthcore_incidents.constants import (
    RULE_LABELS,
    VALID_CATEGORIES,
    VALID_CLINICS,
    VALID_CSV_STATUSES,
)
from healthcore_incidents.csv_validation import ViolationRule, load_incidents, validate_record

VALID_STATUSES = VALID_CSV_STATUSES

SATISFACTION_LABELS: dict[int, str] = {
    1: "Very dissatisfied",
    2: "Dissatisfied",
    3: "Neutral",
    4: "Satisfied",
    5: "Very satisfied",
}

RULE_ORDER = [
    "invalid_clinic_id",
    "country_clinic_mismatch",
    "invalid_category",
    "empty_description",
    "missing_patient_id",
    "closed_no_score",
    "score_out_of_range",
]

CATEGORY_ORDER = [
    "APPOINTMENT",
    "BILLING",
    "CLINICAL_CARE",
    "ACCESSIBILITY",
    "ADMINISTRATIVE",
]

STATUS_ORDER = ["OPEN", "CLOSED", "DISCARDED"]
COUNTRY_ORDER = ["US", "UK"]


@dataclass
class BreakdownItem:
    label: str
    count: int
    percentage: float | None = None


@dataclass
class InvalidBreakdownItem:
    rule: str
    label: str
    count: int


@dataclass
class SatisfactionDistributionItem:
    score: int
    label: str
    count: int


@dataclass
class SatisfactionResult:
    scored_cases: int
    total_closed: int
    average: float | None
    max_score: int = 5
    distribution: list[SatisfactionDistributionItem] = field(default_factory=list)


@dataclass
class TotalsResult:
    total: int
    valid: int
    invalid: int


@dataclass
class AnalysisResult:
    source_filename: str
    analyzed_at: str
    totals: TotalsResult
    invalid_breakdown: list[InvalidBreakdownItem]
    by_category: list[BreakdownItem]
    by_status: list[BreakdownItem]
    by_country: list[BreakdownItem]
    satisfaction: SatisfactionResult


FileInput = Union[str, Path, TextIO, BinaryIO, StringIO]


def _is_blank(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and pd.isna(value):
        return True
    return str(value).strip() == ""


def _parse_score(value: object) -> int | None:
    if _is_blank(value):
        return None
    try:
        return int(float(str(value).strip()))
    except ValueError:
        return None


def _percentage(count: int, total: int) -> float | None:
    if total == 0:
        return None
    return round(count / total * 100, 1)


def analyze(df: pd.DataFrame, source_filename: str) -> AnalysisResult:
    """Analyze incidents and return structured aggregate results."""
    rule_counts = {rule: 0 for rule in RULE_ORDER}
    valid_rows: list[pd.Series] = []

    for _, row in df.iterrows():
        violations = validate_record(row)
        if violations:
            for violation in violations:
                rule_counts[violation.value] += 1
        else:
            valid_rows.append(row)

    valid_df = pd.DataFrame(valid_rows) if valid_rows else pd.DataFrame(columns=df.columns)
    valid_count = len(valid_df)
    total_count = len(df)
    invalid_count = total_count - valid_count

    invalid_breakdown = [
        InvalidBreakdownItem(rule=rule, label=RULE_LABELS[rule], count=rule_counts[rule])
        for rule in RULE_ORDER
        if rule_counts[rule] > 0
    ]

    by_category = [
        BreakdownItem(
            label=cat,
            count=int((valid_df["category"] == cat).sum()) if valid_count else 0,
            percentage=_percentage(
                int((valid_df["category"] == cat).sum()) if valid_count else 0,
                valid_count,
            ),
        )
        for cat in CATEGORY_ORDER
    ]

    by_status = [
        BreakdownItem(
            label=status,
            count=int((valid_df["status"] == status).sum()) if valid_count else 0,
            percentage=_percentage(
                int((valid_df["status"] == status).sum()) if valid_count else 0,
                valid_count,
            ),
        )
        for status in STATUS_ORDER
    ]

    by_country = [
        BreakdownItem(
            label=country,
            count=int((valid_df["country"] == country).sum()) if valid_count else 0,
            percentage=_percentage(
                int((valid_df["country"] == country).sum()) if valid_count else 0,
                valid_count,
            ),
        )
        for country in COUNTRY_ORDER
    ]

    closed_valid = (
        valid_df[valid_df["status"] == "CLOSED"] if valid_count else pd.DataFrame(columns=df.columns)
    )
    total_closed = len(closed_valid)
    scores = (
        closed_valid["satisfaction_score"].apply(_parse_score).dropna().astype(int).tolist()
        if total_closed
        else []
    )
    scored_cases = len(scores)
    average = round(sum(scores) / scored_cases, 2) if scored_cases else None

    score_counts = {score: 0 for score in range(1, 6)}
    for score in scores:
        score_counts[score] += 1

    distribution = [
        SatisfactionDistributionItem(
            score=score,
            label=SATISFACTION_LABELS[score],
            count=score_counts[score],
        )
        for score in range(1, 6)
    ]

    return AnalysisResult(
        source_filename=source_filename,
        analyzed_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        totals=TotalsResult(total=total_count, valid=valid_count, invalid=invalid_count),
        invalid_breakdown=invalid_breakdown,
        by_category=by_category,
        by_status=by_status,
        by_country=by_country,
        satisfaction=SatisfactionResult(
            scored_cases=scored_cases,
            total_closed=total_closed,
            average=average,
            distribution=distribution,
        ),
    )


def to_export_rows(result: AnalysisResult) -> list[dict[str, str | float | None]]:
    """Convert analysis result to CSV export rows."""
    rows: list[dict[str, str | float | None]] = [
        {"metric": "total_records", "value": result.totals.total, "percentage": None},
        {"metric": "valid_records", "value": result.totals.valid, "percentage": None},
        {"metric": "invalid_records", "value": result.totals.invalid, "percentage": None},
    ]

    for item in result.invalid_breakdown:
        rows.append({"metric": item.rule, "value": item.count, "percentage": None})

    for item in result.by_category:
        rows.append(
            {
                "metric": f"category_{item.label}",
                "value": item.count,
                "percentage": item.percentage,
            }
        )

    for item in result.by_status:
        rows.append(
            {
                "metric": f"status_{item.label}",
                "value": item.count,
                "percentage": item.percentage,
            }
        )

    for item in result.by_country:
        rows.append(
            {
                "metric": f"country_{item.label}",
                "value": item.count,
                "percentage": item.percentage,
            }
        )

    if result.satisfaction.average is not None:
        rows.append(
            {
                "metric": "satisfaction_average",
                "value": result.satisfaction.average,
                "percentage": None,
            }
        )

    rows.append(
        {
            "metric": "satisfaction_scored_cases",
            "value": result.satisfaction.scored_cases,
            "percentage": None,
        }
    )

    for item in result.satisfaction.distribution:
        rows.append(
            {
                "metric": f"satisfaction_score_{item.score}",
                "value": item.count,
                "percentage": None,
            }
        )

    return rows
