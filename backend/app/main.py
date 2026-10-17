from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title="gratyPL demo")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    settings.media_root.mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=settings.media_root), name="media")
    return app


app = create_app()
