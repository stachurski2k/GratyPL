from datetime import date, datetime, timedelta, timezone

from app.models import WeeklySummary

BASE = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)


def collect(client, limit):
    items, cursor, pages = [], None, 0
    while True:
        params = {"limit": limit} | ({"cursor": cursor} if cursor else {})
        r = client.get("/api/feed", params=params)
        assert r.status_code == 200, r.text
        body = r.json()
        assert len(body["items"]) <= limit
        items += body["items"]
        pages += 1
        cursor = body["next_cursor"]
        if cursor is None:
            return items, pages


def test_feed_mixes_reports_and_summaries_newest_first(client, make_report, db):
    reports = [make_report(created_at=BASE + timedelta(hours=i)) for i in range(5)]
    summary = WeeklySummary(
        week_start=date(2026, 9, 28),
        generated_at=BASE + timedelta(hours=2, minutes=30),
        report_count=0,
        bbox=None,
        snapshot=[],
    )
    db.add(summary)
    db.commit()

    items, _ = collect(client, limit=50)
    assert [(i["type"], i["id"]) for i in items] == [
        ("report", str(reports[4].id)),
        ("report", str(reports[3].id)),
        ("summary", str(summary.id)),
        ("report", str(reports[2].id)),
        ("report", str(reports[1].id)),
        ("report", str(reports[0].id)),
    ]
    feed_summary = items[2]
    assert feed_summary["week_start"] == "2026-09-28"
    assert feed_summary["week_end"] == "2026-10-05"
    assert items[0]["location"] == [18.67, 50.29]


def test_feed_pagination_walks_everything_once(client, make_report):
    # Część zgłoszeń z identycznym czasem: kursor musi rozstrzygać po id.
    times = [BASE, BASE, BASE, BASE + timedelta(minutes=1), BASE + timedelta(minutes=2)] * 2
    created = {str(make_report(created_at=t).id) for t in times}

    items, pages = collect(client, limit=3)
    ids = [i["id"] for i in items]
    assert len(ids) == len(set(ids)) == len(created)
    assert set(ids) == created
    assert pages == 4
    keys = [(i["created_at"], i["id"]) for i in items]
    assert keys == sorted(keys, reverse=True)


def test_feed_rejects_bad_cursor_and_limit(client):
    assert client.get("/api/feed", params={"cursor": "śmieci"}).status_code == 422
    assert client.get("/api/feed", params={"limit": 0}).status_code == 422
    assert client.get("/api/feed", params={"limit": 51}).status_code == 422
    assert client.get("/api/feed").json() == {"items": [], "next_cursor": None}
