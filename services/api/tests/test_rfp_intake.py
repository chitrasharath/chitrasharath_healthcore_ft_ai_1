from __future__ import annotations

import io
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.core.db import get_supabase_db
from app.domains.jobs.models import JobRun  # noqa: F401
from app.domains.rfp_intake.models import (  # noqa: F401
    DepartmentSection,
    EvaluationResult,
    FinalDocument,
    RfpArbitrationRecord,
    RfpExecutionLog,
    RfpMetadata,
    Ticket,
)
from app.main import app

test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@pytest.fixture(name="rfp_client")
def rfp_client_fixture(tmp_path, monkeypatch):
    SQLModel.metadata.create_all(test_engine)

    def override():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_supabase_db] = override

    # Auth bypass via dependency override
    from app.core.dependencies import get_current_user

    app.dependency_overrides[get_current_user] = lambda: {"id": 1, "email": "tom@healthcore.test"}

    monkeypatch.setattr(
        "app.domains.rfp_intake.service.RAW_DIR",
        tmp_path / "raw",
    )

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
    SQLModel.metadata.drop_all(test_engine)


def _tiny_pdf() -> bytes:
    return b"%PDF-1.1\n%\xe2\xe3\xcf\xd3\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def test_upload_requires_auth():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/rfp-intake/uploads",
            files={"file": ("x.pdf", io.BytesIO(_tiny_pdf()), "application/pdf")},
        )
    assert response.status_code in (401, 403)


def test_upload_rejects_non_pdf(rfp_client: TestClient):
    response = rfp_client.post(
        "/api/v1/rfp-intake/uploads",
        files={"file": ("x.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert response.status_code == 415


def test_upload_accepted_202(rfp_client: TestClient):
    with patch("app.domains.rfp_intake.service._run_background"):
        response = rfp_client.post(
            "/api/v1/rfp-intake/uploads",
            files={"file": ("rfp.pdf", io.BytesIO(_tiny_pdf()), "application/pdf")},
        )
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "analyzing"
    assert body["ticket_id"]
    assert body["rfp_id"].startswith("RFP-")

    detail = rfp_client.get(f"/api/v1/rfp-intake/tickets/{body['ticket_id']}")
    assert detail.status_code == 200
    assert detail.json()["status"] == "analyzing"


def test_upload_idempotent_same_sha(rfp_client: TestClient):
    pdf = _tiny_pdf()
    with patch("app.domains.rfp_intake.service._run_background"):
        first = rfp_client.post(
            "/api/v1/rfp-intake/uploads",
            files={"file": ("a.pdf", io.BytesIO(pdf), "application/pdf")},
        )
        # Mark first as intake_complete so second returns existing
        with Session(test_engine) as session:
            ticket = session.get(Ticket, first.json()["ticket_id"])
            assert ticket is not None
            ticket.status = "intake_complete"
            ticket.updated_at = datetime.now(timezone.utc)
            session.add(ticket)
            session.commit()

        second = rfp_client.post(
            "/api/v1/rfp-intake/uploads",
            files={"file": ("b.pdf", io.BytesIO(pdf), "application/pdf")},
        )
    assert first.status_code == 202
    assert second.status_code == 202
    assert second.json()["ticket_id"] == first.json()["ticket_id"]


def test_list_tickets(rfp_client: TestClient):
    with patch("app.domains.rfp_intake.service._run_background"):
        rfp_client.post(
            "/api/v1/rfp-intake/uploads",
            files={"file": ("rfp.pdf", io.BytesIO(_tiny_pdf()), "application/pdf")},
        )
    response = rfp_client.get("/api/v1/rfp-intake/tickets")
    assert response.status_code == 200
    assert len(response.json()) >= 1


def _seed_intake_complete(ticket_id: str) -> None:
    with Session(test_engine) as session:
        ticket = session.get(Ticket, ticket_id)
        assert ticket is not None
        ticket.status = "intake_complete"
        ticket.updated_at = datetime.now(timezone.utc)
        session.add(ticket)
        for dept in ("revenue", "clinical", "compliance"):
            session.add(
                DepartmentSection(
                    ticket_id=ticket_id,
                    department_id=dept,
                    key_aspects=[f"{dept} aspect"],
                )
            )
        session.commit()


def test_start_drafting_enqueues(rfp_client: TestClient):
    with patch("app.domains.rfp_intake.service._run_background"):
        uploaded = rfp_client.post(
            "/api/v1/rfp-intake/uploads",
            files={"file": ("rfp.pdf", io.BytesIO(_tiny_pdf()), "application/pdf")},
        )
    ticket_id = uploaded.json()["ticket_id"]
    _seed_intake_complete(ticket_id)

    with patch("app.domains.rfp_intake.service._run_drafting_background") as bg:
        response = rfp_client.post(f"/api/v1/rfp-intake/tickets/{ticket_id}/start-drafting")
    assert response.status_code == 202
    assert response.json()["status"] == "drafting"
    bg.assert_called_once()

    detail = rfp_client.get(f"/api/v1/rfp-intake/tickets/{ticket_id}")
    assert detail.json()["status"] == "drafting"


def test_start_drafting_idempotent_when_already_drafting(rfp_client: TestClient):
    with patch("app.domains.rfp_intake.service._run_background"):
        uploaded = rfp_client.post(
            "/api/v1/rfp-intake/uploads",
            files={"file": ("rfp.pdf", io.BytesIO(_tiny_pdf()), "application/pdf")},
        )
    ticket_id = uploaded.json()["ticket_id"]
    _seed_intake_complete(ticket_id)

    with patch("app.domains.rfp_intake.service._run_drafting_background"):
        first = rfp_client.post(f"/api/v1/rfp-intake/tickets/{ticket_id}/start-drafting")
        second = rfp_client.post(f"/api/v1/rfp-intake/tickets/{ticket_id}/start-drafting")
    assert first.status_code == 202
    assert second.status_code == 202
    assert second.json()["status"] == "drafting"


def test_start_drafting_409_wrong_state(rfp_client: TestClient):
    with patch("app.domains.rfp_intake.service._run_background"):
        uploaded = rfp_client.post(
            "/api/v1/rfp-intake/uploads",
            files={"file": ("rfp.pdf", io.BytesIO(_tiny_pdf()), "application/pdf")},
        )
    ticket_id = uploaded.json()["ticket_id"]
    # still analyzing
    response = rfp_client.post(f"/api/v1/rfp-intake/tickets/{ticket_id}/start-drafting")
    assert response.status_code == 409


def test_redraft_only_needs_human_review(rfp_client: TestClient):
    with patch("app.domains.rfp_intake.service._run_background"):
        uploaded = rfp_client.post(
            "/api/v1/rfp-intake/uploads",
            files={"file": ("rfp.pdf", io.BytesIO(_tiny_pdf()), "application/pdf")},
        )
    ticket_id = uploaded.json()["ticket_id"]
    _seed_intake_complete(ticket_id)
    with Session(test_engine) as session:
        ticket = session.get(Ticket, ticket_id)
        assert ticket is not None
        ticket.status = "under_evaluation"
        session.add(ticket)
        from sqlmodel import select

        section = session.exec(
            select(DepartmentSection).where(
                DepartmentSection.ticket_id == ticket_id,
                DepartmentSection.department_id == "revenue",
            )
        ).first()
        assert section is not None
        section.status = "passed"
        session.add(section)
        session.commit()

    bad = rfp_client.post(
        f"/api/v1/rfp-intake/tickets/{ticket_id}/redraft",
        params={"department_id": "revenue"},
    )
    assert bad.status_code == 409

    with Session(test_engine) as session:
        section = session.exec(
            select(DepartmentSection).where(
                DepartmentSection.ticket_id == ticket_id,
                DepartmentSection.department_id == "revenue",
            )
        ).first()
        assert section is not None
        section.status = "needs_human_review"
        session.add(section)
        session.commit()

    with patch("app.domains.rfp_intake.service._run_drafting_background") as bg:
        ok = rfp_client.post(
            f"/api/v1/rfp-intake/tickets/{ticket_id}/redraft",
            params={"department_id": "revenue"},
        )
    assert ok.status_code == 202
    bg.assert_called_once()


def test_send_for_approval_requires_all_passed(rfp_client: TestClient):
    from sqlmodel import select

    with patch("app.domains.rfp_intake.service._run_background"):
        uploaded = rfp_client.post(
            "/api/v1/rfp-intake/uploads",
            files={"file": ("rfp.pdf", io.BytesIO(_tiny_pdf()), "application/pdf")},
        )
    ticket_id = uploaded.json()["ticket_id"]
    _seed_intake_complete(ticket_id)
    with Session(test_engine) as session:
        ticket = session.get(Ticket, ticket_id)
        assert ticket is not None
        ticket.status = "under_evaluation"
        session.add(ticket)
        for section in session.exec(
            select(DepartmentSection).where(DepartmentSection.ticket_id == ticket_id)
        ).all():
            section.status = "passed"
            session.add(section)
        session.commit()

    with patch("app.domains.rfp_intake.service._run_approval_background") as bg:
        response = rfp_client.post(
            f"/api/v1/rfp-intake/tickets/{ticket_id}/send-for-approval"
        )
    assert response.status_code == 202
    bg.assert_called_once()


def test_run_all_from_pdf_enqueues(rfp_client: TestClient):
    with patch("app.domains.rfp_intake.service._run_all_background") as bg:
        response = rfp_client.post(
            "/api/v1/rfp-intake/run-all",
            files={"file": ("rfp.pdf", io.BytesIO(_tiny_pdf()), "application/pdf")},
        )
    assert response.status_code == 202
    assert "ticket_id" in response.json()
    bg.assert_called_once()


def test_decision_validates_owner(rfp_client: TestClient):
    from sqlmodel import select

    with patch("app.domains.rfp_intake.service._run_background"):
        uploaded = rfp_client.post(
            "/api/v1/rfp-intake/uploads",
            files={"file": ("rfp.pdf", io.BytesIO(_tiny_pdf()), "application/pdf")},
        )
    ticket_id = uploaded.json()["ticket_id"]
    _seed_intake_complete(ticket_id)
    with Session(test_engine) as session:
        ticket = session.get(Ticket, ticket_id)
        assert ticket is not None
        ticket.status = "waiting_for_approval"
        session.add(ticket)
        for section in session.exec(
            select(DepartmentSection).where(DepartmentSection.ticket_id == ticket_id)
        ).all():
            section.status = "passed"
            section.approval_status = "pending"
            session.add(section)
        session.commit()

    bad = rfp_client.post(
        f"/api/v1/rfp-intake/tickets/{ticket_id}/departments/revenue/decision",
        json={
            "decision": "approve",
            "approver": "Claire Whitfield",
        },
    )
    assert bad.status_code == 400


def test_delete_ticket(rfp_client: TestClient):
    with patch("app.domains.rfp_intake.service._run_background"):
        uploaded = rfp_client.post(
            "/api/v1/rfp-intake/uploads",
            files={"file": ("rfp.pdf", io.BytesIO(_tiny_pdf()), "application/pdf")},
        )
    ticket_id = uploaded.json()["ticket_id"]
    _seed_intake_complete(ticket_id)

    deleted = rfp_client.delete(f"/api/v1/rfp-intake/tickets/{ticket_id}")
    assert deleted.status_code == 204

    missing = rfp_client.get(f"/api/v1/rfp-intake/tickets/{ticket_id}")
    assert missing.status_code == 404

    again = rfp_client.delete(f"/api/v1/rfp-intake/tickets/{ticket_id}")
    assert again.status_code == 404
