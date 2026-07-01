from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from healthcore_incidents import (
    validate_create_fields as shared_validate_create_fields,
    validate_status_value as shared_validate_status_value,
    validate_transition as shared_validate_transition,
)
from sqlmodel import Session, select

from app.domains.incidents.constants import VALID_CATEGORIES, VALID_ORIGINS, VALID_STATUSES
from app.domains.incidents.models import Incident
from app.domains.incidents.schemas import IncidentCreate, IncidentRead, IncidentSummary


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_read(incident: Incident) -> IncidentRead:
    return IncidentRead.model_validate(incident)


def _raise_if_invalid(error) -> None:
    if error is not None:
        raise HTTPException(status_code=400, detail=error.detail)


def create_incident(session: Session, body: IncidentCreate) -> IncidentRead:
    _raise_if_invalid(
        shared_validate_create_fields(
            title=body.title,
            description=body.description,
            category=body.category,
            origin=body.origin,
            branch=body.branch,
        )
    )
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
    _raise_if_invalid(
        shared_validate_create_fields(
            title=body.title,
            description=body.description,
            category=body.category,
            origin=body.origin,
            branch=body.branch,
        )
    )
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
        _, error = shared_validate_status_value(status)
        _raise_if_invalid(error)
        statement = statement.where(Incident.status == status)
    if origin is not None:
        from healthcore_incidents import validate_origin

        _raise_if_invalid(validate_origin(origin))
        statement = statement.where(Incident.origin == origin)
    if branch is not None:
        from healthcore_incidents import validate_branch

        _raise_if_invalid(validate_branch(branch))
        statement = statement.where(Incident.branch == branch)
    if category is not None:
        from healthcore_incidents import validate_category

        _raise_if_invalid(validate_category(category))
        statement = statement.where(Incident.category == category)
    incidents = session.exec(statement).all()
    return [_to_read(item) for item in incidents]


def get_incident_or_404(session: Session, incident_pk: int) -> Incident:
    incident = session.get(Incident, incident_pk)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found.")
    return incident


def update_status(session: Session, incident_pk: int, new_status: str) -> IncidentRead:
    status, error = shared_validate_status_value(new_status)
    _raise_if_invalid(error)
    incident = get_incident_or_404(session, incident_pk)
    _raise_if_invalid(shared_validate_transition(incident.status, status))
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
