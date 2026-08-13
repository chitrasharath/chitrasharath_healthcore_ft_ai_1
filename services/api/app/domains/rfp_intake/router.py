from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, Response, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse
from sqlmodel import Session

from app.core.db import get_supabase_db
from app.core.dependencies import get_current_user
from app.domains.rfp_intake import service
from app.domains.rfp_intake.schemas import (
    ApprovalAccepted,
    DecisionAccepted,
    DepartmentDecisionBody,
    DraftingAccepted,
    FinalDocumentOut,
    RedraftAccepted,
    ReleaseRedactedAccepted,
    RerunAccepted,
    RunAllAccepted,
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


@router.post("/run-all", response_model=RunAllAccepted, status_code=202)
async def run_all_phases(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    session: Session = Depends(get_supabase_db),
    current_user: dict = Depends(get_current_user),
) -> RunAllAccepted:
    _ = current_user
    return await service.run_all_from_pdf(session, file, background_tasks)


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


@router.delete("/tickets/{ticket_id}", status_code=204)
def delete_ticket(
    ticket_id: str,
    session: Session = Depends(get_supabase_db),
    current_user: dict = Depends(get_current_user),
) -> Response:
    _ = current_user
    service.delete_ticket(session, ticket_id)
    return Response(status_code=204)


@router.post("/tickets/{ticket_id}/rerun", response_model=RerunAccepted, status_code=202)
def rerun_ticket(
    ticket_id: str,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_supabase_db),
    current_user: dict = Depends(get_current_user),
) -> RerunAccepted:
    _ = current_user
    return service.rerun_ticket(session, ticket_id, background_tasks)


@router.post(
    "/tickets/{ticket_id}/start-drafting",
    response_model=DraftingAccepted,
    status_code=202,
)
def start_drafting(
    ticket_id: str,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_supabase_db),
    current_user: dict = Depends(get_current_user),
    continue_to_approval: bool = Query(False),
) -> DraftingAccepted:
    _ = current_user
    return service.start_drafting(
        session,
        ticket_id,
        background_tasks,
        continue_to_approval=continue_to_approval,
    )


@router.post(
    "/tickets/{ticket_id}/send-for-approval",
    response_model=ApprovalAccepted,
    status_code=202,
)
def send_for_approval(
    ticket_id: str,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_supabase_db),
    current_user: dict = Depends(get_current_user),
) -> ApprovalAccepted:
    _ = current_user
    return service.send_for_approval(session, ticket_id, background_tasks)


@router.post(
    "/tickets/{ticket_id}/departments/{department_id}/decision",
    response_model=DecisionAccepted,
)
def department_decision(
    ticket_id: str,
    department_id: str,
    body: DepartmentDecisionBody,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_supabase_db),
    current_user: dict = Depends(get_current_user),
) -> DecisionAccepted:
    _ = current_user
    return service.apply_department_decision(
        session, ticket_id, department_id, body, background_tasks
    )


@router.get(
    "/tickets/{ticket_id}/final-document",
    response_model=FinalDocumentOut,
)
def final_document(
    ticket_id: str,
    session: Session = Depends(get_supabase_db),
    current_user: dict = Depends(get_current_user),
) -> FinalDocumentOut:
    _ = current_user
    return service.get_final_document(session, ticket_id)


@router.get("/tickets/{ticket_id}/final-document/markdown")
def final_document_markdown(
    ticket_id: str,
    session: Session = Depends(get_supabase_db),
    current_user: dict = Depends(get_current_user),
) -> PlainTextResponse:
    _ = current_user
    doc = service.get_final_document(session, ticket_id)
    return PlainTextResponse(
        doc.rendered_markdown or "",
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{ticket_id}_final.md"',
        },
    )


@router.get("/tickets/{ticket_id}/final-document/pdf")
def final_document_pdf(
    ticket_id: str,
    session: Session = Depends(get_supabase_db),
    current_user: dict = Depends(get_current_user),
) -> FileResponse:
    _ = current_user
    path = service.get_final_document_pdf_path(session, ticket_id)
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=f"{ticket_id}_final.pdf",
    )


@router.post(
    "/tickets/{ticket_id}/redraft",
    response_model=RedraftAccepted,
    status_code=202,
)
def redraft_section(
    ticket_id: str,
    background_tasks: BackgroundTasks,
    department_id: str,
    session: Session = Depends(get_supabase_db),
    current_user: dict = Depends(get_current_user),
) -> RedraftAccepted:
    _ = current_user
    return service.redraft_section(session, ticket_id, department_id, background_tasks)


@router.post(
    "/tickets/{ticket_id}/release-redacted",
    response_model=ReleaseRedactedAccepted,
)
def release_redacted(
    ticket_id: str,
    department_id: str,
    session: Session = Depends(get_supabase_db),
    current_user: dict = Depends(get_current_user),
) -> ReleaseRedactedAccepted:
    _ = current_user
    return service.release_redacted_section(session, ticket_id, department_id)
