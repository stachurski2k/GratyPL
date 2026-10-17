from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic_settings import BaseSettings, SettingsConfigDict

# Strefa, w której liczymy tygodnie raportów i interpretujemy czas z EXIF.
WARSAW = ZoneInfo("Europe/Warsaw")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://gratypl:gratypl@localhost:5433/gratypl"
    media_root: Path = Path("media")
    cors_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
