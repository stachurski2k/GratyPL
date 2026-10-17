from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://gratypl:gratypl@localhost:5433/gratypl"
    media_root: Path = Path("media")
    cors_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
