from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import feed, reports, summaries
from app.config import settings
from app.mcp_server import mcp
from app.services.errors import Conflict, InvalidInput, NotFound, ServiceError

STATUS_BY_ERROR = {InvalidInput: 422, NotFound: 404, Conflict: 409}


def create_app() -> FastAPI:
    # Każde wywołanie tworzy nowy session manager MCP, więc create_app można wołać wielokrotnie (testy).
    mcp_app = mcp.streamable_http_app(streamable_http_path="/mcp", stateless_http=True)
    session_manager = mcp.session_manager

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with session_manager.run():
            yield

    app = FastAPI(title="gratyPL demo", lifespan=lifespan)
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
    app.include_router(summaries.router)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    settings.media_root.mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=settings.media_root), name="media")
    # Montowane na końcu pod "/": aplikacja MCP obsługuje tylko ścieżkę /mcp.
    app.mount("/", mcp_app)
    return app


app = create_app()
