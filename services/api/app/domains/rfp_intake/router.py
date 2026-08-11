from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from sqlmodel import Session

from app.core.db import get_supabase_db
from app.core.dependencies import get_current_user
from app.domains.rfp_intake import service
from app.domains.rfp_intake.schemas import (
    RerunAccepted,
    TicketDetail,
    TicketSummary,
    UploadAccepted,
)

router = APIRouter(prefix="/rfp-intake", tags=["rfp-intake"])


@router.post("/uploads", response_model=UploadAccepted, status_code=202)
async def upload_rfp(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    session: Session = Depends(get_supabase_db),
    current_user: dict = Depends(get_current_user),
) -> UploadAccepted:
    _ = current_user
    return await service.upload_pdf(session, file, background_tasks)


@router.get("/tickets", response_model=list[TicketSummary])
def list_tickets(
    session: Session = Depends(get_supabase_db),
    current_user: dict = Depends(get_current_user),
) -> list[TicketSummary]:
    _ = current_user
    return service.list_ticket_summaries(session)


@router.get("/tickets/{ticket_id}", response_model=TicketDetail)
def get_ticket(
    ticket_id: str,
    session: Session = Depends(get_supabase_db),
    current_user: dict = Depends(get_current_user),
) -> TicketDetail:
    _ = current_user
    return service.get_ticket_detail(session, ticket_id)


@router.post("/tickets/{ticket_id}/rerun", response_model=RerunAccepted, status_code=202)
def rerun_ticket(
    ticket_id: str,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_supabase_db),
    current_user: dict = Depends(get_current_user),
) -> RerunAccepted:
    _ = current_user
    return service.rerun_ticket(session, ticket_id, background_tasks)
