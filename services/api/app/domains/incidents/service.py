from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlmodel import Session, select

from app.domains.incidents.constants import (
    FINAL_STATUSES,
    STATUS_DISPLAY,
    STATUS_TRANSITION_ORDER,
    STATUS_TRANSITIONS,
    VALID_BRANCHES,
    VALID_CATEGORIES,
    VALID_ORIGINS,
    VALID_STATUSES,
)
from app.domains.incidents.models import Incident
from app.domains.incidents.schemas import IncidentCreate, IncidentRead, IncidentSummary


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_read(incident: Incident) -> IncidentRead:
    return IncidentRead.model_validate(incident)


def _validate_title(title: str | None) -> None:
    if title is None:
        raise HTTPException(status_code=400, detail="Title is required.")
    if not str(title).strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty.")


def _validate_description(description: str | None) -> None:
    if description is None:
        raise HTTPException(status_code=400, detail="Description is required.")
    if not str(description).strip():
        raise HTTPException(status_code=400, detail="Description cannot be empty.")


def _validate_category(category: str | None) -> None:
    if category is None or not str(category).strip():
        raise HTTPException(status_code=400, detail="Field 'category' is required.")
    value = str(category).strip()
    if value not in VALID_CATEGORIES:
        options = ", ".join(sorted(VALID_CATEGORIES))
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category '{value}'. Must be one of: {options}.",
        )


def _validate_status_value(status: str | None) -> str:
    if status is None or not str(status).strip():
        raise HTTPException(status_code=400, detail="Field 'status' is required.")
    value = str(status).strip()
    if value not in VALID_STATUSES:
        options = ", ".join(sorted(VALID_STATUSES))
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{value}'. Must be one of: {options}.",
        )
    return value


def _validate_origin(origin: str | None) -> None:
    if origin is None or not str(origin).strip():
        raise HTTPException(status_code=400, detail="Field 'origin' is required.")
    value = str(origin).strip()
    if value not in VALID_ORIGINS:
        options = ", ".join(sorted(VALID_ORIGINS))
        raise HTTPException(
            status_code=400,
            detail=f"Invalid origin '{value}'. Must be one of: {options}.",
        )


def _validate_branch(branch: str | None) -> None:
    if branch is None or not str(branch).strip():
        raise HTTPException(status_code=400, detail="Field 'branch' is required.")
    value = str(branch).strip()
    if value not in VALID_BRANCHES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid branch '{value}'. Must be one of the 12 clinic codes (e.g., US-TX-01) or 'Central'.",
        )


def validate_create_fields(body: IncidentCreate) -> None:
    _validate_title(body.title)
    _validate_description(body.description)
    _validate_category(body.category)
    _validate_origin(body.origin)
    _validate_branch(body.branch)


def validate_transition(current: str, requested: str) -> None:
    if current in FINAL_STATUSES:
        label = STATUS_DISPLAY.get(current, current.capitalize())
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from '{current}' to '{requested}'. {label} is a final state.",
        )
    allowed = STATUS_TRANSITIONS.get(current, frozenset())
    if requested not in allowed:
        ordered = [s for s in STATUS_TRANSITION_ORDER if s in allowed]
        valid_list = ", ".join(ordered)
        raise HTTPException(
            status_code=400,
            detail=(
                f"Cannot transition from '{current}' to '{requested}'. "
                f"Valid transitions: {valid_list}."
            ),
        )


def create_incident(session: Session, body: IncidentCreate) -> IncidentRead:
    validate_create_fields(body)
    now = _utc_now()
    incident = Incident(
        title=str(body.title).strip(),
        description=str(body.description).strip(),
        category=str(body.category).strip(),
        status="open",
        origin=str(body.origin).strip(),
        branch=str(body.branch).strip(),
        incident_id=None,
        created_at=now,
        updated_at=now,
    )
    session.add(incident)
    session.commit()
    session.refresh(incident)
    return _to_read(incident)


def update_incident(session: Session, incident_pk: int, body: IncidentCreate) -> IncidentRead:
    validate_create_fields(body)
    incident = get_incident_or_404(session, incident_pk)
    incident.title = str(body.title).strip()
    incident.description = str(body.description).strip()
    incident.category = str(body.category).strip()
    incident.origin = str(body.origin).strip()
    incident.branch = str(body.branch).strip()
    incident.updated_at = _utc_now()
    session.add(incident)
    session.commit()
    session.refresh(incident)
    return _to_read(incident)


def list_incidents(
    session: Session,
    *,
    status: str | None = None,
    origin: str | None = None,
    branch: str | None = None,
    category: str | None = None,
) -> list[IncidentRead]:
    statement = select(Incident)
    if status is not None:
        _validate_status_value(status)
        statement = statement.where(Incident.status == status)
    if origin is not None:
        _validate_origin(origin)
        statement = statement.where(Incident.origin == origin)
    if branch is not None:
        _validate_branch(branch)
        statement = statement.where(Incident.branch == branch)
    if category is not None:
        _validate_category(category)
        statement = statement.where(Incident.category == category)
    incidents = session.exec(statement).all()
    return [_to_read(item) for item in incidents]


def get_incident_or_404(session: Session, incident_pk: int) -> Incident:
    incident = session.get(Incident, incident_pk)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found.")
    return incident


def update_status(session: Session, incident_pk: int, new_status: str) -> IncidentRead:
    status = _validate_status_value(new_status)
    incident = get_incident_or_404(session, incident_pk)
    validate_transition(incident.status, status)
    incident.status = status
    incident.updated_at = _utc_now()
    session.add(incident)
    session.commit()
    session.refresh(incident)
    return _to_read(incident)


def build_summary(session: Session) -> IncidentSummary:
    incidents = session.exec(select(Incident)).all()

    by_status = {key: 0 for key in sorted(VALID_STATUSES)}
    by_category = {key: 0 for key in sorted(VALID_CATEGORIES)}
    by_origin = {key: 0 for key in sorted(VALID_ORIGINS)}
    by_branch: dict[str, int] = {}

    for item in incidents:
        by_status[item.status] = by_status.get(item.status, 0) + 1
        by_category[item.category] = by_category.get(item.category, 0) + 1
        by_origin[item.origin] = by_origin.get(item.origin, 0) + 1
        if item.branch:
            by_branch[item.branch] = by_branch.get(item.branch, 0) + 1

    by_branch = {k: v for k, v in by_branch.items() if v > 0}

    return IncidentSummary(
        by_status=by_status,
        by_category=by_category,
        by_origin=by_origin,
        by_branch=by_branch,
    )
