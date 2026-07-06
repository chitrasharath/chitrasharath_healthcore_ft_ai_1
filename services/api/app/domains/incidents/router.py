from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.db import get_supabase_db
from app.domains.incidents.schemas import IncidentCreate, IncidentRead, IncidentSummary, IncidentUpdate, StatusUpdate
from app.domains.incidents import service

router = APIRouter(prefix="/incidents", tags=["incident-management"])


@router.post("", response_model=IncidentRead, status_code=201)
def create_incident(
    body: IncidentCreate,
    session: Session = Depends(get_supabase_db),
) -> IncidentRead:
    return service.create_incident(session, body)


@router.get("", response_model=list[IncidentRead])
def list_incidents(
    session: Session = Depends(get_supabase_db),
    status: str | None = None,
    origin: str | None = None,
    branch: str | None = None,
    category: str | None = None,
) -> list[IncidentRead]:
    return service.list_incidents(
        session,
        status=status,
        origin=origin,
        branch=branch,
        category=category,
    )


@router.get("/summary", response_model=IncidentSummary)
def incident_summary(session: Session = Depends(get_supabase_db)) -> IncidentSummary:
    return service.build_summary(session)


@router.get("/{incident_pk}", response_model=IncidentRead)
def get_incident(
    incident_pk: int,
    session: Session = Depends(get_supabase_db),
) -> IncidentRead:
    incident = service.get_incident_or_404(session, incident_pk)
    return IncidentRead.model_validate(incident)


@router.patch("/{incident_pk}/status", response_model=IncidentRead)
def patch_incident_status(
    incident_pk: int,
    body: StatusUpdate,
    session: Session = Depends(get_supabase_db),
) -> IncidentRead:
    return service.update_status(session, incident_pk, body.status)


@router.patch("/{incident_pk}", response_model=IncidentRead)
def patch_incident(
    incident_pk: int,
    body: IncidentUpdate,
    session: Session = Depends(get_supabase_db),
) -> IncidentRead:
    return service.update_incident(session, incident_pk, body)
