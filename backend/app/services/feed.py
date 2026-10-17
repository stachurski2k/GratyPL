"""Feed: zgłoszenia i raporty tygodniowe w jednym strumieniu, paginacja kursorowa."""

import base64
import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import literal, select, tuple_, union_all
from sqlalchemy.orm import Session, selectinload

from app.models import Report, WeeklySummary
from app.services.errors import InvalidInput

DEFAULT_LIMIT = 20
MAX_LIMIT = 50


@dataclass
class FeedResult:
    items: list[Report | WeeklySummary]
    next_cursor: str | None


def encode_cursor(ts: datetime, item_id: uuid.UUID) -> str:
    return base64.urlsafe_b64encode(f"{ts.isoformat()}|{item_id}".encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        ts, item_id = base64.urlsafe_b64decode(cursor.encode()).decode().split("|")
        parsed = datetime.fromisoformat(ts)
        if parsed.tzinfo is None:
            raise ValueError
        return parsed, uuid.UUID(item_id)
    except ValueError:
        raise InvalidInput("Niepoprawny kursor.") from None


def list_feed(session: Session, limit: int = DEFAULT_LIMIT, cursor: str | None = None) -> FeedResult:
    """Posty od najnowszych: zgłoszenia po created_at, raporty po generated_at."""
    if not 1 <= limit <= MAX_LIMIT:
        raise InvalidInput(f"limit musi być z zakresu 1–{MAX_LIMIT}.")

    reports = select(
        literal("report").label("kind"), Report.id.label("id"), Report.created_at.label("ts")
    ).where(Report.deleted_at.is_(None))
    summaries = select(
        literal("summary").label("kind"),
        WeeklySummary.id.label("id"),
        WeeklySummary.generated_at.label("ts"),
    )
    posts = union_all(reports, summaries).subquery()

    query = select(posts.c.kind, posts.c.id, posts.c.ts)
    if cursor:
        ts, item_id = decode_cursor(cursor)
        query = query.where(tuple_(posts.c.ts, posts.c.id) < tuple_(literal(ts), literal(item_id)))
    rows = session.execute(
        query.order_by(posts.c.ts.desc(), posts.c.id.desc()).limit(limit + 1)
    ).all()

    page, has_more = rows[:limit], len(rows) > limit
    report_ids = [r.id for r in page if r.kind == "report"]
    summary_ids = [r.id for r in page if r.kind == "summary"]
    by_id: dict[uuid.UUID, Report | WeeklySummary] = {}
    if report_ids:
        by_id.update(
            (r.id, r)
            for r in session.scalars(
                select(Report).where(Report.id.in_(report_ids)).options(selectinload(Report.photos))
            )
        )
    if summary_ids:
        by_id.update(
            (s.id, s)
            for s in session.scalars(select(WeeklySummary).where(WeeklySummary.id.in_(summary_ids)))
        )

    next_cursor = encode_cursor(page[-1].ts, page[-1].id) if has_more else None
    return FeedResult(items=[by_id[r.id] for r in page], next_cursor=next_cursor)
