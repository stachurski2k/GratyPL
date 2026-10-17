from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import feed, reports
from app.config import settings
from app.services.errors import Conflict, InvalidInput, NotFound, ServiceError

STATUS_BY_ERROR = {InvalidInput: 422, NotFound: 404, Conflict: 409}


def create_app() -> FastAPI:
    app = FastAPI(title="gratyPL demo")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(ServiceError)
    def service_error(request: Request, exc: ServiceError) -> JSONResponse:
        return JSONResponse({"detail": exc.message}, status_code=STATUS_BY_ERROR.get(type(exc), 400))

    app.include_router(reports.router)
    app.include_router(feed.router)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    settings.media_root.mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=settings.media_root), name="media")
    return app


app = create_app()
