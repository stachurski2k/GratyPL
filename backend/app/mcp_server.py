"""Serwer MCP dla agentów AI: odczyt feedu, zgłoszeń i raportów oraz usuwanie zgłoszeń.

Narzędzia są cienkie: wołają te same serwisy co REST (bez zapytań HTTP do API).
Zgłoszeń nie da się tu tworzyć (zdjęcia przez argumenty narzędzi są niepraktyczne).
"""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from typing import Annotated, Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field
from sqlalchemy.orm import Session

from app import db
from app.schemas import BBox, FeedPage, ReportOut, SummaryOut, feature_collection, feed_item
from app.services import feed, reports, summaries
from app.services.errors import ServiceError

mcp = MCPServer(
    name="gratyPL",
    instructions=(
        "gratyPL (demo) zbiera zgłoszenia porzuconych samochodów w Gliwicach, Zabrzu i okolicach "
        "oraz tygodniowe raporty. Współrzędne zawsze jako [lng, lat] (WGS84). Tygodnie liczone są "
        "w strefie Europe/Warsaw od poniedziałku. Zgłoszenia ze źródłem 'seed' to dane przykładowe."
    ),
)


@contextmanager
def _session() -> Iterator[Session]:
    """Sesja bazy na jedno wywołanie narzędzia; błędy serwisów trafiają do modelu jako ToolError."""
    with db.SessionLocal() as session:
        try:
            yield session
        except ServiceError as e:
            raise ToolError(e.message) from None


@mcp.tool()
def list_feed(
    limit: Annotated[int, Field(ge=1, le=feed.MAX_LIMIT)] = feed.DEFAULT_LIMIT,
    cursor: Annotated[str | None, Field(description="next_cursor z poprzedniej strony")] = None,
) -> FeedPage:
    """Strumień postów od najnowszych: zgłoszenia (type=report) i raporty tygodniowe (type=summary)."""
    with _session() as session:
        result = feed.list_feed(session, limit=limit, cursor=cursor)
        return FeedPage(items=[feed_item(i) for i in result.items], next_cursor=result.next_cursor)


@mcp.tool()
def get_report(id: uuid.UUID) -> ReportOut:
    """Jedno aktywne zgłoszenie (z lokalizacją [lng, lat] i adresami zdjęć)."""
    with _session() as session:
        return ReportOut.from_model(reports.get_report(session, id))


@mcp.tool()
def get_reports_in_area(
    min_lng: float, min_lat: float, max_lng: float, max_lat: float
) -> dict[str, Any]:
    """Aktywne zgłoszenia w prostokącie jako GeoJSON FeatureCollection (współrzędne [lng, lat])."""
    try:
        bbox = BBox(min_lng=min_lng, min_lat=min_lat, max_lng=max_lng, max_lat=max_lat)
    except ValueError:
        raise ToolError(
            "Niepoprawny obszar: współrzędne poza zakresem albo min >= max."
        ) from None
    with _session() as session:
        return feature_collection(reports.reports_in_area(session, bbox))


@mcp.tool()
def get_weekly_summary(
    week_start: Annotated[date, Field(description="Poniedziałek tygodnia, YYYY-MM-DD")],
) -> SummaryOut:
    """Raport tygodniowy (snapshot zgłoszeń z chwili generowania)."""
    with _session() as session:
        return SummaryOut.from_model(summaries.get_summary(session, week_start))


@mcp.tool()
def delete_report(id: uuid.UUID) -> str:
    """Usuwa zgłoszenie (soft delete; znika z feedu i mapy, raporty tygodniowe zostają bez zmian).

    Operacja jest idempotentna. Przed użyciem upewnij się, że użytkownik naprawdę tego chce.
    """
    with _session() as session:
        reports.delete_report(session, id)
    return f"Zgłoszenie {id} zostało usunięte."
