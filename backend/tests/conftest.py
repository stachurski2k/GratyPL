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


@pytest.fixture
def client(db, tmp_path, monkeypatch):
    from app import config
    from app.db import get_session
    from app.main import create_app

    monkeypatch.setattr(config.settings, "media_root", tmp_path / "media")
    app = create_app()
    app.dependency_overrides[get_session] = lambda: db
    with TestClient(app) as c:
        yield c
