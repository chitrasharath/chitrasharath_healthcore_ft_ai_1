from __future__ import annotations

from dataclasses import dataclass

from healthcore_incidents.constants import (
    FINAL_STATUSES,
    STATUS_DISPLAY,
    STATUS_TRANSITION_ORDER,
    STATUS_TRANSITIONS,
    VALID_BRANCHES,
    VALID_CATEGORIES,
    VALID_ORIGINS,
    VALID_STATUSES,
)


@dataclass(frozen=True)
class ValidationErrorDetail:
    detail: str


def validate_title(title: str | None) -> ValidationErrorDetail | None:
    if title is None:
        return ValidationErrorDetail("Title is required.")
    if not str(title).strip():
        return ValidationErrorDetail("Title cannot be empty.")
    return None


def validate_description(description: str | None) -> ValidationErrorDetail | None:
    if description is None:
        return ValidationErrorDetail("Description is required.")
    if not str(description).strip():
        return ValidationErrorDetail("Description cannot be empty.")
    return None


def validate_category(category: str | None) -> ValidationErrorDetail | None:
    if category is None or not str(category).strip():
        return ValidationErrorDetail("Field 'category' is required.")
    value = str(category).strip()
    if value not in VALID_CATEGORIES:
        options = ", ".join(sorted(VALID_CATEGORIES))
        return ValidationErrorDetail(
            f"Invalid category '{value}'. Must be one of: {options}."
        )
    return None


def validate_status_value(status: str | None) -> tuple[str | None, ValidationErrorDetail | None]:
    if status is None or not str(status).strip():
        return None, ValidationErrorDetail("Field 'status' is required.")
    value = str(status).strip()
    if value not in VALID_STATUSES:
        options = ", ".join(sorted(VALID_STATUSES))
        return None, ValidationErrorDetail(
            f"Invalid status '{value}'. Must be one of: {options}."
        )
    return value, None


def validate_origin(origin: str | None) -> ValidationErrorDetail | None:
    if origin is None or not str(origin).strip():
        return ValidationErrorDetail("Field 'origin' is required.")
    value = str(origin).strip()
    if value not in VALID_ORIGINS:
        options = ", ".join(sorted(VALID_ORIGINS))
        return ValidationErrorDetail(
            f"Invalid origin '{value}'. Must be one of: {options}."
        )
    return None


def validate_branch(branch: str | None) -> ValidationErrorDetail | None:
    if branch is None or not str(branch).strip():
        return ValidationErrorDetail("Field 'branch' is required.")
    value = str(branch).strip()
    if value not in VALID_BRANCHES:
        return ValidationErrorDetail(
            "Invalid branch '{value}'. Must be one of the 12 clinic codes (e.g., US-TX-01) or 'Central'.".format(
                value=value
            )
        )
    return None


def validate_create_fields(
    *,
    title: str | None,
    description: str | None,
    category: str | None,
    origin: str | None,
    branch: str | None,
) -> ValidationErrorDetail | None:
    for validator, value in (
        (validate_title, title),
        (validate_description, description),
        (validate_category, category),
        (validate_origin, origin),
        (validate_branch, branch),
    ):
        error = validator(value)
        if error is not None:
            return error
    return None


def validate_transition(current: str, requested: str) -> ValidationErrorDetail | None:
    if current in FINAL_STATUSES:
        label = STATUS_DISPLAY.get(current, current.capitalize())
        return ValidationErrorDetail(
            f"Cannot transition from '{current}' to '{requested}'. {label} is a final state."
        )
    allowed = STATUS_TRANSITIONS.get(current, frozenset())
    if requested not in allowed:
        ordered = [status for status in STATUS_TRANSITION_ORDER if status in allowed]
        valid_list = ", ".join(ordered)
        return ValidationErrorDetail(
            f"Cannot transition from '{current}' to '{requested}'. Valid transitions: {valid_list}."
        )
    return None
