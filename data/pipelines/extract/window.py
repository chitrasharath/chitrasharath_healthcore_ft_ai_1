from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlmodel import Session

from data.pipelines.config import LOOKBACK_DAYS, REPROCESS_WINDOW_DAYS
from data.pipelines.load import repository as repo


def resolve_window(
    start: datetime | None,
    end: datetime | None,
    session: Session,
) -> tuple[datetime, datetime]:
    watermark_to = end or datetime.now(timezone.utc)
    if watermark_to.tzinfo is None:
        watermark_to = watermark_to.replace(tzinfo=timezone.utc)
    else:
        watermark_to = watermark_to.astimezone(timezone.utc)

    if start is not None:
        watermark_from = start
        if watermark_from.tzinfo is None:
            watermark_from = watermark_from.replace(tzinfo=timezone.utc)
        else:
            watermark_from = watermark_from.astimezone(timezone.utc)
        return watermark_from, watermark_to

    prior = repo.get_latest_success_watermark_to(session)
    if prior is None:
        watermark_from = watermark_to - timedelta(days=LOOKBACK_DAYS)
    else:
        prior_utc = prior if prior.tzinfo else prior.replace(tzinfo=timezone.utc)
        watermark_from = prior_utc.astimezone(timezone.utc) - timedelta(
            days=REPROCESS_WINDOW_DAYS,
        )
    return watermark_from, watermark_to
