"""Raporty tygodniowe: generowanie ręczne, odczyt.

Tydzień to [poniedziałek 00:00, następny poniedziałek 00:00) w strefie Europe/Warsaw.
Raport jest samowystarczalny: kopiuje dane i miniatury zgłoszeń w chwili generowania.
"""

import uuid
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import WARSAW
from app.models import Report, WeeklySummary
from app.services import media
from app.services.errors import Conflict, InvalidInput, NotFound


def week_start_of(moment: datetime) -> date:
    """Poniedziałek (czas warszawski) tygodnia, do którego należy dana chwila."""
    local = moment.astimezone(WARSAW).date()
    return local - timedelta(days=local.weekday())


def week_bounds(week_start: date) -> tuple[datetime, datetime]:
    """Granice tygodnia w UTC; uwzględniają zmianę czasu letniego/zimowego."""
    if week_start.weekday() != 0:
        raise InvalidInput(f"{week_start.isoformat()} to nie poniedziałek.")
    start = datetime.combine(week_start, time(0), tzinfo=WARSAW)
    end = datetime.combine(week_start + timedelta(days=7), time(0), tzinfo=WARSAW)
    return start.astimezone(timezone.utc), end.astimezone(timezone.utc)


def get_summary(session: Session, week_start: date) -> WeeklySummary:
    summary = session.scalars(
        select(WeeklySummary).where(WeeklySummary.week_start == week_start)
    ).one_or_none()
    if summary is None:
        raise NotFound(f"Brak raportu dla tygodnia od {week_start.isoformat()}.")
    return summary


def generate_summary(
    session: Session,
    week_start: date,
    force: bool = False,
    generated_at: datetime | None = None,
) -> WeeklySummary:
    """Tworzy raport tygodnia; istniejący zastępuje tylko przy force=True (inaczej Conflict).

    generated_at domyślnie to teraz; seeder ustawia go na chwilę po końcu tygodnia.
    """
    start, end = week_bounds(week_start)
    if start > datetime.now(timezone.utc):
        raise InvalidInput("Nie można wygenerować raportu dla tygodnia, który się jeszcze nie zaczął.")

    existing = session.scalars(
        select(WeeklySummary).where(WeeklySummary.week_start == week_start)
    ).one_or_none()
    if existing is not None and not force:
        raise Conflict(f"Raport dla tygodnia od {week_start.isoformat()} już istnieje.")

    reports = list(
        session.scalars(
            select(Report)
            .where(Report.deleted_at.is_(None), Report.created_at >= start, Report.created_at < end)
            .order_by(Report.created_at, Report.id)
            .options(selectinload(Report.photos))
        )
    )

    # Każda wersja raportu ma własny katalog, więc zastąpienie nie nadpisuje plików
    # starej wersji, dopóki nowa nie zostanie zapisana w bazie.
    summary_id = uuid.uuid4()
    directory = f"summaries/{week_start.isoformat()}/{summary_id}"
    try:
        snapshot = [_snapshot_item(r, directory) for r in reports]
        if existing is not None:
            session.delete(existing)
            session.flush()  # zwolnij unikalne week_start przed wstawieniem nowego wiersza
        summary = WeeklySummary(
            id=summary_id,
            week_start=week_start,
            report_count=len(reports),
            bbox=_bbox(reports),
            snapshot=snapshot,
        )
        if generated_at is not None:
            summary.generated_at = generated_at
        session.add(summary)
        session.commit()
    except Exception:
        session.rollback()
        media.remove_dir(directory)
        raise

    if existing is not None:
        media.remove_dir(f"summaries/{week_start.isoformat()}/{existing.id}")
    session.refresh(summary)
    return summary


def _snapshot_item(report: Report, directory: str) -> dict:
    thumbs = []
    for photo in report.photos:
        dest = f"{directory}/{report.id}_{photo.position:02d}.jpg"
        media.copy_file(photo.thumb_path, dest)
        thumbs.append(dest)
    return {
        "id": str(report.id),
        "created_at": report.created_at.isoformat(),
        "location": [report.lng, report.lat],
        "description": report.description,
        "has_plates": report.has_plates,
        "thumbs": thumbs,
    }


def _bbox(reports: list[Report]) -> list[float] | None:
    if not reports:
        return None
    lngs = [r.lng for r in reports]
    lats = [r.lat for r in reports]
    return [min(lngs), min(lats), max(lngs), max(lats)]
