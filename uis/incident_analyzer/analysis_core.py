"""Shared incident analysis logic for CLI and API."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from io import StringIO
from pathlib import Path
from typing import BinaryIO, TextIO, Union

import pandas as pd

VALID_CLINICS: dict[str, str] = {
    "US-TX-01": "US",
    "US-TX-02": "US",
    "US-TX-03": "US",
    "US-FL-01": "US",
    "US-FL-02": "US",
    "US-FL-03": "US",
    "US-GA-01": "US",
    "US-GA-02": "US",
    "US-GA-03": "US",
    "UK-LON-01": "UK",
    "UK-LON-02": "UK",
    "UK-MAN-01": "UK",
}

VALID_CATEGORIES = frozenset(
    {"APPOINTMENT", "BILLING", "CLINICAL_CARE", "ACCESSIBILITY", "ADMINISTRATIVE"}
)

VALID_STATUSES = frozenset({"OPEN", "CLOSED", "DISCARDED"})

PATIENT_ID_PATTERN = re.compile(r"^PAT-\d{6}$")

SATISFACTION_LABELS: dict[int, str] = {
    1: "Very dissatisfied",
    2: "Dissatisfied",
    3: "Neutral",
    4: "Satisfied",
    5: "Very satisfied",
}

RULE_LABELS: dict[str, str] = {
    "invalid_clinic_id": "Invalid or missing clinic_id",
    "country_clinic_mismatch": "Country/clinic mismatch",
    "invalid_category": "Invalid or missing category",
    "empty_description": "Empty description",
    "missing_patient_id": "Missing patient_id",
    "closed_no_score": "Closed case, no score",
    "score_out_of_range": "Satisfaction score out of range",
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


class ViolationRule(str, Enum):
    INVALID_CLINIC_ID = "invalid_clinic_id"
    COUNTRY_CLINIC_MISMATCH = "country_clinic_mismatch"
    INVALID_CATEGORY = "invalid_category"
    EMPTY_DESCRIPTION = "empty_description"
    MISSING_PATIENT_ID = "missing_patient_id"
    CLOSED_NO_SCORE = "closed_no_score"
    SCORE_OUT_OF_RANGE = "score_out_of_range"


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


def load_incidents(source: FileInput) -> pd.DataFrame:
    """Load incidents CSV from path or file-like object."""
    return pd.read_csv(source, dtype=str, keep_default_na=False)


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


def validate_record(row: pd.Series) -> list[ViolationRule]:
    """Return violation rules for a row; never includes PHI."""
    violations: list[ViolationRule] = []

    clinic_id = str(row.get("clinic_id", "")).strip()
    country = str(row.get("country", "")).strip()
    category = str(row.get("category", "")).strip()
    description = str(row.get("description", "")).strip()
    status = str(row.get("status", "")).strip()
    patient_id = str(row.get("patient_id", "")).strip()
    score = _parse_score(row.get("satisfaction_score"))

    if not clinic_id or clinic_id not in VALID_CLINICS:
        violations.append(ViolationRule.INVALID_CLINIC_ID)
    elif country != VALID_CLINICS[clinic_id]:
        violations.append(ViolationRule.COUNTRY_CLINIC_MISMATCH)

    if not category or category not in VALID_CATEGORIES:
        violations.append(ViolationRule.INVALID_CATEGORY)

    if len(description) < 5:
        violations.append(ViolationRule.EMPTY_DESCRIPTION)

    if not patient_id or not PATIENT_ID_PATTERN.match(patient_id):
        violations.append(ViolationRule.MISSING_PATIENT_ID)

    if score is not None and (score < 1 or score > 5):
        violations.append(ViolationRule.SCORE_OUT_OF_RANGE)

    if status == "CLOSED" and score is None:
        violations.append(ViolationRule.CLOSED_NO_SCORE)

    return violations


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
