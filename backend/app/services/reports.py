"""Zgłoszenia: tworzenie, odczyt, wyszukiwanie po obszarze i soft delete."""

import uuid
from datetime import datetime, timezone

from geoalchemy2 import Geography
from sqlalchemy import cast, func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Report, ReportPhoto
from app.schemas import BBox, Point
from app.services import media
from app.services.errors import InvalidInput, NotFound

MIN_PHOTOS = 1
MAX_PHOTOS = 5
MAX_DESCRIPTION = 2000
MISSING_LOCATION = (
    "Brak lokalizacji: wskaż punkt na mapie albo dodaj zdjęcie z zapisanymi współrzędnymi GPS."
)


def create_report(
    session: Session,
    photos: list[media.PhotoUpload],
    location: Point | None = None,
    description: str | None = None,
    has_plates: bool | None = None,
    source: str = "web",
    created_at: datetime | None = None,
) -> Report:
    """Tworzy zgłoszenie. Lokalizacja: z argumentu, a gdy jej brak, z GPS w EXIF zdjęć."""
    if not MIN_PHOTOS <= len(photos) <= MAX_PHOTOS:
        raise InvalidInput(f"Zgłoszenie musi mieć od {MIN_PHOTOS} do {MAX_PHOTOS} zdjęć.")
    description = (description or "").strip() or None
    if description and len(description) > MAX_DESCRIPTION:
        raise InvalidInput(f"Opis może mieć najwyżej {MAX_DESCRIPTION} znaków.")

    parsed = [media.parse_photo(p) for p in photos]
    if location is None:
        gps = next((p.gps for p in parsed if p.gps), None)
        if gps is None:
            raise InvalidInput(MISSING_LOCATION)
        location = Point(lng=gps[0], lat=gps[1])

    report = Report(
        id=uuid.uuid4(),
        location=location.to_ewkt(),
        description=description,
        has_plates=has_plates,
        source=source,
    )
    if created_at is not None:
        report.created_at = created_at

    directory = f"reports/{report.id}"
    try:
        for position, photo in enumerate(parsed):
            stored = media.store_photo(photo, directory, f"{position:02d}")
            report.photos.append(
                ReportPhoto(
                    path=stored.path,
                    thumb_path=stored.thumb_path,
                    taken_at=photo.taken_at,
                    position=position,
                )
            )
        session.add(report)
        session.commit()
    except Exception:
        session.rollback()
        media.remove_dir(directory)
        raise
    session.refresh(report)
    return report


def _active_reports():
    return select(Report).where(Report.deleted_at.is_(None)).options(selectinload(Report.photos))


def get_report(session: Session, report_id: uuid.UUID) -> Report:
    report = session.scalars(_active_reports().where(Report.id == report_id)).one_or_none()
    if report is None:
        raise NotFound("Nie znaleziono zgłoszenia.")
    return report


def delete_report(session: Session, report_id: uuid.UUID) -> None:
    """Soft delete. Idempotentne: ponowne usunięcie nie jest błędem."""
    report = session.get(Report, report_id)
    if report is None:
        raise NotFound("Nie znaleziono zgłoszenia.")
    if report.deleted_at is None:
        report.deleted_at = datetime.now(timezone.utc)
        session.commit()


def reports_in_area(session: Session, bbox: BBox, limit: int = 1000) -> list[Report]:
    """Aktywne zgłoszenia w prostokącie (operator && korzysta z indeksu GiST)."""
    envelope = cast(func.ST_MakeEnvelope(*bbox.as_list(), 4326), Geography)
    query = (
        _active_reports()
        .where(Report.location.op("&&")(envelope))
        .order_by(Report.created_at.desc(), Report.id.desc())
        .limit(limit)
    )
    return list(session.scalars(query))
