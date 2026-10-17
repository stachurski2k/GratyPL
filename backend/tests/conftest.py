import os

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://gratypl:gratypl@localhost:5434/gratypl_test"
)
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="session")
def engine():
    """Świeży schemat z migracji Alembica na testowej bazie PostGIS."""
    engine = create_engine(TEST_DATABASE_URL)
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public"))
    cfg = Config(os.path.join(BACKEND_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(BACKEND_DIR, "alembic"))
    cfg.attributes["database_url"] = TEST_DATABASE_URL
    command.upgrade(cfg, "head")
    yield engine
    engine.dispose()


@pytest.fixture
def db(engine):
    """Sesja z czystymi tabelami dla każdego testu."""
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE reports, report_photos, weekly_summaries CASCADE"))
    with Session(engine, expire_on_commit=False) as session:
        yield session


@pytest.fixture(autouse=True)
def media_root(tmp_path, monkeypatch):
    from app.config import settings

    root = tmp_path / "media"
    monkeypatch.setattr(settings, "media_root", root)
    return root


@pytest.fixture
def client(db, media_root):
    from app.db import get_session
    from app.main import create_app

    app = create_app()
    app.dependency_overrides[get_session] = lambda: db
    with TestClient(app) as c:
        yield c


@pytest.fixture
def make_report(db):
    """Tworzy zgłoszenie przez serwis (ta sama ścieżka co upload)."""
    from app.schemas import Point
    from app.services import reports
    from app.services.media import PhotoUpload
    from tests.images import make_image

    def _make(lng=18.67, lat=50.29, created_at=None, **kwargs):
        photos = [PhotoUpload("a.jpg", make_image(size=(64, 48)))]
        return reports.create_report(
            db, photos, location=Point(lng=lng, lat=lat), created_at=created_at, **kwargs
        )

    return _make
