from datetime import datetime, timezone

from PIL import Image

from tests.images import make_image

GLIWICE = (18.67, 50.29)
ZABRZE = (18.79, 50.31)
KRAKOW = (19.94, 50.06)


def jpeg(**kwargs) -> tuple[str, bytes, str]:
    return ("car.jpg", make_image(**kwargs), "image/jpeg")


def post_report(client, photos, **data):
    return client.post("/api/reports", files=[("photos", p) for p in photos], data=data)


def test_create_with_form_location(client, media_root):
    r = post_report(
        client,
        [jpeg(), ("car.png", make_image("PNG", size=(600, 800)), "image/png")],
        lng="18.67",
        lat="50.29",
        description="  Golf bez kół  ",
        has_plates="false",
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["location"] == [18.67, 50.29]
    assert body["description"] == "Golf bez kół"
    assert body["has_plates"] is False
    assert body["source"] == "web"
    assert len(body["photos"]) == 2

    for photo in body["photos"]:
        assert client.get(photo["url"]).status_code == 200
        thumb = media_root / photo["thumb_url"].removeprefix("/media/")
        with Image.open(thumb) as img:
            assert max(img.size) == 480
    assert body["photos"][0]["url"].startswith(f"/media/reports/{body['id']}/")


def test_create_with_location_from_exif(client):
    taken = datetime(2026, 7, 1, 14, 30)  # czas lokalny z aparatu (CEST, UTC+2)
    r = post_report(client, [jpeg(), jpeg(gps=(18.6767, 50.2945), taken_at=taken)])
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["location"] == [18.6767, 50.2945]
    assert body["has_plates"] is None
    assert body["photos"][0]["taken_at"] is None
    assert body["photos"][1]["taken_at"] == "2026-07-01T12:30:00Z"


def test_form_location_wins_over_exif(client):
    r = post_report(client, [jpeg(gps=KRAKOW)], lng=str(GLIWICE[0]), lat=str(GLIWICE[1]))
    assert r.json()["location"] == list(GLIWICE)


def test_missing_location_is_422(client, media_root):
    r = post_report(client, [jpeg()])
    assert r.status_code == 422
    assert "lokalizacji" in r.json()["detail"]
    assert not (media_root / "reports").exists() or not any((media_root / "reports").iterdir())


def test_partial_or_invalid_coordinates_are_422(client):
    assert post_report(client, [jpeg()], lng="18.67").status_code == 422
    assert post_report(client, [jpeg()], lng="200", lat="50").status_code == 422


def test_photo_validation(client):
    loc = {"lng": "18.67", "lat": "50.29"}
    assert post_report(client, [], **loc).status_code == 422
    assert post_report(client, [jpeg(size=(8, 8))] * 6, **loc).status_code == 422
    not_image = ("x.jpg", b"to nie jest obrazek", "image/jpeg")
    assert post_report(client, [not_image], **loc).status_code == 422
    gif = ("x.gif", make_image("GIF", size=(8, 8)), "image/gif")
    assert "JPEG" in post_report(client, [gif], **loc).json()["detail"]
    too_big = ("big.jpg", b"\xff" * (10 * 1024 * 1024 + 1), "image/jpeg")
    assert "10 MB" in post_report(client, [too_big], **loc).json()["detail"]


def test_get_report_returns_lng_lat(client, make_report):
    report = make_report(*GLIWICE)
    r = client.get(f"/api/reports/{report.id}")
    assert r.status_code == 200
    assert r.json()["location"] == [18.67, 50.29]
    assert client.get("/api/reports/00000000-0000-0000-0000-000000000000").status_code == 404


def test_geojson_bbox_filter_and_coordinate_order(client, make_report):
    gliwice = make_report(*GLIWICE)
    zabrze = make_report(*ZABRZE)
    make_report(*KRAKOW)

    r = client.get("/api/reports/geojson", params={"bbox": "18.6,50.25,18.85,50.35"})
    assert r.status_code == 200
    fc = r.json()
    assert fc["type"] == "FeatureCollection"
    ids = {f["id"] for f in fc["features"]}
    assert ids == {str(gliwice.id), str(zabrze.id)}
    feature = next(f for f in fc["features"] if f["id"] == str(gliwice.id))
    assert feature["geometry"] == {"type": "Point", "coordinates": [18.67, 50.29]}
    assert feature["properties"]["thumb_url"].endswith("_thumb.jpg")

    only_gliwice = client.get("/api/reports/geojson", params={"bbox": "18.6,50.25,18.7,50.3"})
    assert [f["id"] for f in only_gliwice.json()["features"]] == [str(gliwice.id)]


def test_geojson_invalid_bbox(client):
    for bbox in ["18,50,19", "a,b,c,d", "19,50,18,51", "18,50,190,51"]:
        r = client.get("/api/reports/geojson", params={"bbox": bbox})
        assert r.status_code == 422, bbox


def test_soft_delete_hides_report_everywhere(client, make_report, db):
    kept = make_report(*GLIWICE, created_at=datetime(2026, 10, 1, tzinfo=timezone.utc))
    gone = make_report(*GLIWICE, created_at=datetime(2026, 10, 2, tzinfo=timezone.utc))

    assert client.delete(f"/api/reports/{gone.id}").status_code == 204

    assert client.get(f"/api/reports/{gone.id}").status_code == 404
    feed_ids = [i["id"] for i in client.get("/api/feed").json()["items"]]
    assert feed_ids == [str(kept.id)]
    map_ids = [
        f["id"]
        for f in client.get("/api/reports/geojson", params={"bbox": "18,50,19,51"}).json()["features"]
    ]
    assert map_ids == [str(kept.id)]

    db.refresh(gone)
    assert gone.deleted_at is not None  # wiersz zostaje w bazie


def test_delete_is_idempotent(client, make_report):
    report = make_report()
    assert client.delete(f"/api/reports/{report.id}").status_code == 204
    assert client.delete(f"/api/reports/{report.id}").status_code == 204
    assert client.delete("/api/reports/00000000-0000-0000-0000-000000000000").status_code == 404
