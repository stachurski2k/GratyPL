import random
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import select

from app.config import WARSAW
from app.models import Report, WeeklySummary
from scripts import seed as seed_script
from scripts.demo_images import demo_car_jpeg

NOW = datetime(2026, 10, 17, 12, 0, tzinfo=timezone.utc)  # sobota
WEEKS = [date(2026, 9, 21), date(2026, 9, 28), date(2026, 10, 5)]


def test_seed_creates_demo_reports_and_summaries(db, media_root):
    result = seed_script.seed(db, now=NOW)
    assert result.reports == len(seed_script.SPOTS) == 15
    assert result.exif_located == 5
    assert result.summaries == WEEKS

    seeded = list(db.scalars(select(Report).order_by(Report.created_at)))
    assert {r.source for r in seeded} == {"seed"}
    assert all(r.description.startswith("[DEMO]") for r in seeded)
    assert all(1 <= len(r.photos) <= 3 for r in seeded)
    assert all(r.created_at < NOW for r in seeded)
    # Każde zgłoszenie trafia w swój punkt, także te z lokalizacją wyłącznie z EXIF.
    expected = sorted((round(lng, 4), round(lat, 4)) for _, lng, lat in seed_script.SPOTS)
    assert sorted((round(r.lng, 4), round(r.lat, 4)) for r in seeded) == expected
    assert all((media_root / r.photos[0].thumb_path).exists() for r in seeded)

    summaries = list(db.scalars(select(WeeklySummary).order_by(WeeklySummary.week_start)))
    assert [s.week_start for s in summaries] == WEEKS
    assert sum(s.report_count for s in summaries) == 15
    assert all(s.report_count > 0 for s in summaries)
    first_generated = summaries[0].generated_at.astimezone(WARSAW)
    assert (first_generated.date(), first_generated.hour) == (date(2026, 9, 28), 8)


def test_seed_is_skipped_when_present_and_reset_recreates(db, media_root):
    seed_script.seed(db, now=NOW)
    assert seed_script.seed(db, now=NOW) is None

    assert seed_script.reset(db) == 15
    assert db.scalars(select(Report)).first() is None
    assert db.scalars(select(WeeklySummary)).first() is None
    assert not any((media_root / "reports").iterdir())

    assert seed_script.seed(db, now=NOW).reports == 15


@pytest.mark.parametrize("number", [1, 2])
def test_demo_images_are_deterministic(number):
    assert demo_car_jpeg(number, random.Random(1)) == demo_car_jpeg(number, random.Random(1))
