"""Dane demo: ~15 przykładowych zgłoszeń w Gliwicach i Zabrzu z 3 ostatnich pełnych tygodni
oraz raporty tygodniowe dla tych tygodni.

Uruchomienie (w katalogu backend/ albo w kontenerze):
    python -m scripts.seed           # pomija, jeśli dane demo już są
    python -m scripts.seed --reset   # usuwa poprzednie dane demo i tworzy je od nowa

Zgłoszenia przechodzą przez tę samą ścieżkę co upload z frontendu (services.reports + media).
Co trzecie zgłoszenie nie ma współrzędnych w formularzu: lokalizacja pochodzi z EXIF zdjęcia.
"""

import argparse
import random
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import WARSAW
from app.db import SessionLocal
from app.models import Report, WeeklySummary
from app.schemas import Point
from app.services import media, reports, summaries
from app.services.media import PhotoUpload
from scripts.demo_images import demo_car_jpeg

SEED = 20261017
WEEKS = 3

# (miejsce, lng, lat). Kilka punktów celowo blisko siebie (garaże na Trynku, Zaborze).
SPOTS = [
    ("Gliwice, okolice Rynku", 18.6714, 50.2945),
    ("Gliwice-Trynek, garaże", 18.6805, 50.2862),
    ("Gliwice-Trynek, garaże", 18.6812, 50.2857),
    ("Gliwice-Trynek, garaże", 18.6798, 50.2866),
    ("Gliwice-Sośnica", 18.7280, 50.2850),
    ("Gliwice-Łabędy", 18.5670, 50.3370),
    ("Gliwice-Sikornik", 18.6450, 50.2780),
    ("Gliwice-Szobiszowice", 18.6950, 50.3050),
    ("Zabrze, centrum", 18.7860, 50.3080),
    ("Zabrze-Mikulczyce", 18.7630, 50.3490),
    ("Zabrze-Biskupice", 18.8380, 50.3200),
    ("Zabrze-Zaborze", 18.7893, 50.2894),
    ("Zabrze-Zaborze", 18.7899, 50.2889),
    ("Knurów", 18.6750, 50.2200),
    ("Pyskowice", 18.6290, 50.3990),
]

DESCRIPTIONS = [
    "Stoi od miesięcy, bez kół, na cegłach.",
    "Wybite szyby, w środku śmieci.",
    "Brak tablic, przebite opony, zarośnięty trawą.",
    "Rozebrany do połowy: brak drzwi i maski.",
    "Zajmuje miejsce parkingowe przy bloku od zeszłej zimy.",
    "Wyciekający olej pod autem, czuć benzynę.",
    None,
    "Ktoś systematycznie wymontowuje części.",
    "Auto po pożarze, nadpalone wnętrze.",
]


@dataclass
class SeedResult:
    reports: int
    exif_located: int
    summaries: list[date]


def seed(session: Session, now: datetime | None = None) -> SeedResult | None:
    """Tworzy dane demo; zwraca None, jeśli już istnieją."""
    if session.scalars(select(Report.id).where(Report.source == "seed").limit(1)).first():
        return None

    now = now or datetime.now(timezone.utc)
    rng = random.Random(SEED)
    current_week = summaries.week_start_of(now)
    weeks = [current_week - timedelta(weeks=WEEKS - i) for i in range(WEEKS)]

    exif_located = 0
    for number, (place, lng, lat) in enumerate(SPOTS, start=1):
        week = weeks[(number - 1) * WEEKS // len(SPOTS)]
        local_day = datetime.combine(week + timedelta(days=rng.randint(0, 6)), time(0), tzinfo=WARSAW)
        created_at = (local_day + timedelta(hours=rng.randint(7, 20), minutes=rng.randint(0, 59))).astimezone(
            timezone.utc
        )
        from_exif = number % 3 == 2
        photo_count = rng.randint(1, 3)
        taken_local = created_at.astimezone(WARSAW).replace(tzinfo=None) - timedelta(minutes=rng.randint(2, 30))
        photos = [
            PhotoUpload(
                filename=f"demo-{number}-{i + 1}.jpg",
                data=demo_car_jpeg(
                    number,
                    rng,
                    # GPS tylko w ostatnim zdjęciu: serwis ma wziąć pierwsze zdjęcie, które go ma.
                    gps=(lng, lat) if from_exif and i == photo_count - 1 else None,
                    taken_at=taken_local,
                ),
            )
            for i in range(photo_count)
        ]
        description = rng.choice(DESCRIPTIONS)
        reports.create_report(
            session,
            photos,
            location=None if from_exif else Point(lng=lng, lat=lat),
            description=f"[DEMO] {place}. {description}" if description else f"[DEMO] {place}.",
            has_plates=rng.choice([True, False, None]),
            source="seed",
            created_at=created_at,
        )
        exif_located += from_exif

    for week in weeks:
        # Raport „powstaje” w poniedziałek rano po zakończonym tygodniu.
        generated_at = datetime.combine(week + timedelta(weeks=1), time(8), tzinfo=WARSAW)
        summaries.generate_summary(
            session, week, force=True, generated_at=min(generated_at.astimezone(timezone.utc), now)
        )

    return SeedResult(reports=len(SPOTS), exif_located=exif_located, summaries=weeks)


def reset(session: Session) -> int:
    """Usuwa (na twardo) zgłoszenia demo, ich pliki i raporty, które je zawierają."""
    seed_reports = list(session.scalars(select(Report).where(Report.source == "seed")))
    seed_ids = {str(r.id) for r in seed_reports}
    for summary in session.scalars(select(WeeklySummary)):
        if any(item["id"] in seed_ids for item in summary.snapshot):
            media.remove_dir(f"summaries/{summary.week_start.isoformat()}/{summary.id}")
            session.delete(summary)
    for report in seed_reports:
        media.remove_dir(f"reports/{report.id}")
        session.delete(report)
    session.commit()
    return len(seed_reports)


def main() -> None:
    parser = argparse.ArgumentParser(description="Dane demo gratyPL")
    parser.add_argument("--reset", action="store_true", help="usuń poprzednie dane demo przed seedowaniem")
    args = parser.parse_args()

    with SessionLocal() as session:
        if args.reset:
            print(f"Usunięto {reset(session)} zgłoszeń demo.")
        result = seed(session)
    if result is None:
        print("Dane demo już istnieją (użyj --reset, żeby utworzyć je od nowa).")
        return
    weeks = ", ".join(w.isoformat() for w in result.summaries)
    print(
        f"Utworzono {result.reports} zgłoszeń demo "
        f"({result.exif_located} z lokalizacją z EXIF) i raporty tygodni: {weeks}."
    )


if __name__ == "__main__":
    main()
