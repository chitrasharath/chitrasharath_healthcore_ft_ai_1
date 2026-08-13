"""Consolidate approved sections into FinalDocument (markdown + PDF)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlmodel import Session

from app.domains.rfp_intake import store
from app.domains.rfp_intake.models import FinalDocument
from data.pipelines.rfp_intake.owners import REQUIRED_DEPARTMENTS
from data.pipelines.rfp_intake.phi import contains_rfp_phi

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
RAW_DIR = REPO_ROOT / "data" / "raw"


def currency_for_country(client_country: str | None) -> str:
    return "GBP" if (client_country or "").strip().upper() == "UK" else "USD"


def render_markdown(
    *,
    ticket_id: str,
    rfp_id: str,
    client_name: str | None,
    client_country: str | None,
    currency: str,
    sections: list[dict[str, Any]],
) -> str:
    lines = [
        f"# HealthCore Institutional Proposal",
        "",
        f"- Ticket: `{ticket_id}`",
        f"- RFP: `{rfp_id}`",
        f"- Client: {client_name or '—'}",
        f"- Country: {client_country or '—'}",
        f"- Currency: {currency}",
        "",
    ]
    order = list(REQUIRED_DEPARTMENTS)
    by_dept = {s["department_id"]: s for s in sections}
    for dept in order:
        section = by_dept.get(dept)
        if section is None:
            continue
        lines.append(f"## {dept.title()}")
        lines.append("")
        lines.append(section.get("draft_content") or "")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _strip_inline_md(text: str) -> str:
    """Remove common inline markdown markers for PDF body text."""
    import re

    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)
    text = re.sub(r"_([^_]+)_", r"\1", text)
    return text


def write_pdf(markdown: str, pdf_path: Path) -> None:
    """Render markdown as a readable PDF (headings, bullets) — not raw source."""
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    width = pdf.epw
    # fpdf2 core fonts are latin-1
    safe = markdown.encode("latin-1", errors="replace").decode("latin-1")

    def _cell(text: str, *, size: int = 11, style: str = "", h: float = 6) -> None:
        pdf.set_font("Helvetica", style=style, size=size)
        pdf.set_x(pdf.l_margin)
        body = text if text.strip() else " "
        try:
            pdf.multi_cell(
                width,
                h,
                body,
                new_x=XPos.LMARGIN,
                new_y=YPos.NEXT,
            )
        except Exception:
            step = max(40, int(width // 2) or 40)
            for i in range(0, max(len(body), 1), step):
                chunk = body[i : i + step] or " "
                pdf.set_x(pdf.l_margin)
                pdf.multi_cell(
                    width,
                    h,
                    chunk,
                    new_x=XPos.LMARGIN,
                    new_y=YPos.NEXT,
                )

    for raw in safe.splitlines():
        line = raw.rstrip()
        if not line.strip():
            pdf.ln(3)
            continue
        stripped = line.lstrip()
        if stripped.startswith("### "):
            _cell(_strip_inline_md(stripped[4:]), size=12, style="B", h=7)
        elif stripped.startswith("## "):
            pdf.ln(2)
            _cell(_strip_inline_md(stripped[3:]), size=14, style="B", h=8)
        elif stripped.startswith("# "):
            _cell(_strip_inline_md(stripped[2:]), size=16, style="B", h=9)
            pdf.ln(2)
        elif stripped.startswith(("- ", "* ")):
            _cell(f"  - {_strip_inline_md(stripped[2:])}", size=11, h=6)
        elif len(stripped) >= 3 and set(stripped) <= {"-", "=", "_"}:
            # horizontal rule — skip visual noise
            pdf.ln(2)
        else:
            _cell(_strip_inline_md(stripped), size=11, h=6)

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(pdf_path))


def compliance_cleared_redactions(sections: list[Any]) -> bool:
    """Every phi_was_redacted section must be Compliance-approved (or the section itself approved)."""
    for section in sections:
        ev = section.evaluation_results or {}
        if not ev.get("phi_was_redacted"):
            continue
        # Compliance must have approved the ticket's compliance section
        # and this section must not still show residual PHI
        if ev.get("contains_phi"):
            return False
    compliance = next(
        (s for s in sections if s.department_id == "compliance"),
        None,
    )
    if compliance is None or compliance.approval_status != "approved":
        # If any redaction existed, compliance approval is mandatory (always is)
        if any((s.evaluation_results or {}).get("phi_was_redacted") for s in sections):
            return False
    return True


def generate_final_document(session: Session, ticket_id: str) -> FinalDocument:
    ticket = store.get_ticket(session, ticket_id)
    if ticket is None:
        raise ValueError(f"ticket not found: {ticket_id}")
    meta = store.get_metadata(session, ticket_id)
    sections = store.list_sections(session, ticket_id)

    for section in sections:
        if section.approval_status != "approved":
            raise ValueError(f"section {section.department_id} not approved")
        if section.status == "needs_human_review":
            raise ValueError(f"section {section.department_id} needs human review")
        if (section.evaluation_results or {}).get("contains_phi"):
            raise ValueError(f"section {section.department_id} still contains PHI")

    if not compliance_cleared_redactions(sections):
        raise ValueError("PHI-redacted sections not cleared by Compliance")

    compliance = next((s for s in sections if s.department_id == "compliance"), None)
    if compliance is None or compliance.approval_status != "approved":
        raise ValueError("Compliance approval is mandatory")

    currency = currency_for_country(meta.client_country if meta else None)
    section_payload = [
        {
            "department_id": s.department_id,
            "draft_content": s.draft_content or "",
        }
        for s in sections
    ]
    md = render_markdown(
        ticket_id=ticket_id,
        rfp_id=ticket.rfp_id,
        client_name=meta.client_name if meta else None,
        client_country=meta.client_country if meta else None,
        currency=currency,
        sections=section_payload,
    )
    hit, _ = contains_rfp_phi(md)
    if hit:
        raise ValueError("Final document PHI gate failed")

    pdf_path = RAW_DIR / f"{ticket_id}_final.pdf"
    write_pdf(md, pdf_path)

    now = datetime.now(timezone.utc)
    row = session.get(FinalDocument, ticket_id)
    if row is None:
        row = FinalDocument(ticket_id=ticket_id, generated_at=now)
    row.sections = section_payload
    row.currency = currency
    row.generated_at = now
    row.rendered_markdown = md
    row.pdf_path = str(pdf_path)
    session.add(row)
    session.flush()
    return row
