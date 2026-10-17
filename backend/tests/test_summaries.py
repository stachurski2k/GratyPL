import shutil
from datetime import date, datetime, timedelta, timezone

import pytest

from app.services.errors import InvalidInput
from app.services.summaries import week_bounds, week_start_of

UTC = timezone.utc
WEEK = date(2025, 10, 20)  # tydzień ze zmianą czasu (niedziela 26.10: CEST -> CET)


def generate(client, week_start=WEEK, force=None):
    params = {"week_start": week_start.isoformat()}
    if force is not None:
        params["force"] = force
    return client.post("/api/summaries/generate", params=params)


def test_week_bounds_follow_warsaw_time_and_dst():
    assert week_bounds(WEEK) == (
        datetime(2025, 10, 19, 22, 0, tzinfo=UTC),  # pon. 00:00 CEST
        datetime(2025, 10, 26, 23, 0, tzinfo=UTC),  # następny pon. 00:00 CET
    )
    assert week_bounds(date(2026, 3, 23)) == (
        datetime(2026, 3, 22, 23, 0, tzinfo=UTC),  # CET
        datetime(2026, 3, 29, 22, 0, tzinfo=UTC),  # CEST po zmianie 29.03
    )
    with pytest.raises(InvalidInput):
        week_bounds(date(2025, 10, 21))


def test_week_start_of_uses_warsaw_date():
    # Niedziela 22:30 UTC to już poniedziałek 00:30 w Warszawie.
    assert week_start_of(datetime(2026, 10, 18, 22, 30, tzinfo=UTC)) == date(2026, 10, 19)
    assert week_start_of(datetime(2026, 10, 18, 21, 59, tzinfo=UTC)) == date(2026, 10, 12)


def test_generate_includes_exactly_the_warsaw_week(client, make_report):
    start, end = week_bounds(WEEK)
    first = make_report(18.60, 50.28, created_at=start)  # pon. 00:00 – włącznie
    last = make_report(18.80, 50.32, created_at=end - timedelta(microseconds=1))
    make_report(created_at=end)  # następny pon. 00:00 – już poza tygodniem
    make_report(created_at=start - timedelta(microseconds=1))
    deleted = make_report(created_at=datetime(2025, 10, 22, 12, tzinfo=UTC))
    client.delete(f"/api/reports/{deleted.id}")

    r = generate(client)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["week_start"] == "2025-10-20"
    assert body["week_end"] == "2025-10-27"
    assert body["report_count"] == 2
    assert [i["id"] for i in body["reports"]] == [str(first.id), str(last.id)]
    assert body["bbox"] == [18.60, 50.28, 18.80, 50.32]
    assert body["reports"][0]["location"] == [18.60, 50.28]

    thumb = body["reports"][0]["thumb_urls"][0]
    assert thumb.startswith("/media/summaries/2025-10-20/")
    assert client.get(thumb).status_code == 200
    assert client.get("/api/summaries/2025-10-20").json() == body


def test_empty_week(client):
    body = generate(client, date(2026, 9, 7)).json()
    assert body["report_count"] == 0
    assert body["bbox"] is None
    assert body["reports"] == []


def test_summary_is_unchanged_after_report_deletion(client, make_report, media_root):
    report = make_report(created_at=datetime(2025, 10, 21, 10, tzinfo=UTC), description="Opel")
    before = generate(client).json()

    assert client.delete(f"/api/reports/{report.id}").status_code == 204
    # Nawet zniknięcie plików zgłoszenia nie psuje raportu: miniatury są skopiowane.
    shutil.rmtree(media_root / "reports")

    after = client.get("/api/summaries/2025-10-20").json()
    assert after == before
    assert after["reports"][0]["description"] == "Opel"
    assert client.get(after["reports"][0]["thumb_urls"][0]).status_code == 200


def test_existing_summary_conflicts_unless_forced(client, make_report, media_root):
    make_report(created_at=datetime(2025, 10, 21, 10, tzinfo=UTC))
    old = generate(client).json()
    old_dir = media_root / old["reports"][0]["thumb_urls"][0].removeprefix("/media/")

    make_report(created_at=datetime(2025, 10, 22, 10, tzinfo=UTC))
    conflict = generate(client)
    assert conflict.status_code == 409
    assert generate(client, force="false").status_code == 409

    new = generate(client, force="true")
    assert new.status_code == 201
    assert new.json()["report_count"] == 2
    assert new.json()["id"] != old["id"]
    assert client.get("/api/summaries/2025-10-20").json() == new.json()
    assert not old_dir.exists()  # pliki zastąpionej wersji posprzątane


def test_generate_validation_and_missing_summary(client):
    assert generate(client, date(2025, 10, 22)).status_code == 422  # środa
    assert generate(client, date(2099, 1, 5)).status_code == 422  # przyszłość
    assert client.get("/api/summaries/2025-10-20").status_code == 404
    assert client.post("/api/summaries/generate", params={"week_start": "zły"}).status_code == 422


def test_generated_summary_appears_in_feed(client, make_report):
    make_report(created_at=datetime(2025, 10, 21, 10, tzinfo=UTC))
    summary = generate(client).json()
    items = client.get("/api/feed").json()["items"]
    assert items[0]["type"] == "summary"
    assert items[0]["id"] == summary["id"]
    assert items[0]["report_count"] == 1
