from __future__ import annotations

import re
from enum import Enum
from io import StringIO
from pathlib import Path
from typing import BinaryIO, TextIO, Union

import pandas as pd

from healthcore_incidents.constants import VALID_CATEGORIES, VALID_CLINICS

PATIENT_ID_PATTERN = re.compile(r"^PAT-\d{6}$")

FileInput = Union[str, Path, TextIO, BinaryIO, StringIO]


class ViolationRule(str, Enum):
    INVALID_CLINIC_ID = "invalid_clinic_id"
    COUNTRY_CLINIC_MISMATCH = "country_clinic_mismatch"
    INVALID_CATEGORY = "invalid_category"
    EMPTY_DESCRIPTION = "empty_description"
    MISSING_PATIENT_ID = "missing_patient_id"
    CLOSED_NO_SCORE = "closed_no_score"
    SCORE_OUT_OF_RANGE = "score_out_of_range"


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
    """Return violation rules for a CSV row; never includes PHI."""
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
