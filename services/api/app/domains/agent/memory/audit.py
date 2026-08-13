"""PHI-free audit log on Redis Stream ``mem:audit``."""

from __future__ import annotations

import logging
import time
from typing import Any

from app.domains.knowledge.pii import redact_pii

logger = logging.getLogger(__name__)

AUDIT_STREAM = "mem:audit"
AUDIT_MAXLEN = 100_000


def _preview(text: str | None, *, omit: bool = False) -> str | None:
    if omit or not text:
        return None
    scrubbed = redact_pii(text) or ""
    return scrubbed[:80]


def append_audit(
    redis_client: Any,
    *,
    event: str,
    staff_id: str | None = None,
    clinic_id: str | None = None,
    proposal_id: str | None = None,
    mem_id: str | None = None,
    decision: str | None = None,
    reasons: str | None = None,
    preview_text: str | None = None,
    omit_preview: bool = False,
    before: int | None = None,
    after: int | None = None,
) -> None:
    """XADD mem:audit — never store raw PHI-rejected text."""
    fields: dict[str, str] = {
        "event": event,
        "ts": str(int(time.time())),
    }
    if staff_id is not None:
        fields["staff_id"] = staff_id
    if clinic_id is not None:
        fields["clinic_id"] = clinic_id
    if proposal_id is not None:
        fields["proposal_id"] = proposal_id
    if mem_id is not None:
        fields["mem_id"] = mem_id
    if decision is not None:
        fields["decision"] = decision
    if reasons is not None:
        fields["reasons"] = reasons
    if before is not None:
        fields["before"] = str(before)
    if after is not None:
        fields["after"] = str(after)
    preview = _preview(preview_text, omit=omit_preview or event == "phi_rejected")
    if preview:
        fields["preview"] = preview

    try:
        redis_client.xadd(AUDIT_STREAM, fields, maxlen=AUDIT_MAXLEN, approximate=True)
    except Exception:
        logger.exception("Failed to append memory audit event=%s", event)

    logger.info(
        "memory_audit event=%s staff_id=%s clinic_id=%s proposal_id=%s",
        event,
        staff_id,
        clinic_id,
        proposal_id,
    )
