from sqlalchemy import func, inspect, select, text

from app.models import Report


def test_migration_creates_tables_and_gist_index(engine):
    insp = inspect(engine)
    assert {"reports", "report_photos", "weekly_summaries"} <= set(insp.get_table_names())
    with engine.connect() as conn:
        indexdef = conn.execute(
            text("SELECT indexdef FROM pg_indexes WHERE indexname = 'ix_reports_location'")
        ).scalar_one()
    assert "USING gist" in indexdef


def test_location_roundtrip_is_lng_lat(db):
    db.add(Report(location="SRID=4326;POINT(18.67 50.29)", source="web"))
    db.commit()
    geom = func.ST_GeomFromWKB(func.ST_AsBinary(Report.location))
    assert db.execute(select(func.ST_X(geom), func.ST_Y(geom))).one() == (18.67, 50.29)


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}
