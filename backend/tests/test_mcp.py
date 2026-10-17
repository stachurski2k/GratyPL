from datetime import datetime, timezone

import pytest
from mcp import Client
from sqlalchemy.orm import sessionmaker

from app import db as app_db
from app.mcp_server import mcp

UTC = timezone.utc
TOOLS = {"list_feed", "get_report", "get_reports_in_area", "get_weekly_summary", "delete_report"}


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def mcp_client(engine, db, monkeypatch):
    """Fabryka klientów MCP in-process; narzędzia otwierają sesje na bazie testowej."""
    monkeypatch.setattr(app_db, "SessionLocal", sessionmaker(bind=engine, expire_on_commit=False))
    return lambda: Client(mcp)


async def call(make_client, tool, **args):
    async with make_client() as client:
        return await client.call_tool(tool, args)


@pytest.mark.anyio
async def test_lists_exactly_the_planned_tools(mcp_client):
    async with mcp_client() as client:
        tools = {t.name for t in (await client.list_tools()).tools}
    assert tools == TOOLS  # w szczególności brak create_report


@pytest.mark.anyio
async def test_get_report_and_area_use_lng_lat(mcp_client, make_report):
    gliwice = make_report(18.67, 50.29)
    make_report(19.94, 50.06)  # Kraków, poza obszarem

    result = await call(mcp_client, "get_report", id=str(gliwice.id))
    assert not result.is_error
    assert result.structured_content["location"] == [18.67, 50.29]

    area = await call(
        mcp_client, "get_reports_in_area", min_lng=18.6, min_lat=50.25, max_lng=18.85, max_lat=50.35
    )
    features = area.structured_content["features"]
    assert [f["id"] for f in features] == [str(gliwice.id)]
    assert features[0]["geometry"]["coordinates"] == [18.67, 50.29]


@pytest.mark.anyio
async def test_list_feed_paginates(mcp_client, make_report):
    for day in range(1, 4):
        make_report(created_at=datetime(2026, 10, day, tzinfo=UTC))
    first = (await call(mcp_client, "list_feed", limit=2)).structured_content
    assert len(first["items"]) == 2 and first["items"][0]["type"] == "report"
    second = (await call(mcp_client, "list_feed", limit=2, cursor=first["next_cursor"])).structured_content
    assert len(second["items"]) == 1 and second["next_cursor"] is None


@pytest.mark.anyio
async def test_delete_report_is_soft_and_idempotent(mcp_client, make_report, db):
    report = make_report()
    for _ in range(2):
        result = await call(mcp_client, "delete_report", id=str(report.id))
        assert not result.is_error
    missing = await call(mcp_client, "get_report", id=str(report.id))
    assert missing.is_error
    assert "Nie znaleziono" in missing.content[0].text
    db.refresh(report)
    assert report.deleted_at is not None


@pytest.mark.anyio
async def test_get_weekly_summary(mcp_client, client, make_report):
    make_report(created_at=datetime(2025, 10, 21, 10, tzinfo=UTC))
    assert client.post("/api/summaries/generate", params={"week_start": "2025-10-20"}).status_code == 201

    result = await call(mcp_client, "get_weekly_summary", week_start="2025-10-20")
    assert result.structured_content["report_count"] == 1
    missing = await call(mcp_client, "get_weekly_summary", week_start="2025-10-13")
    assert missing.is_error and "Brak raportu" in missing.content[0].text


@pytest.mark.anyio
async def test_invalid_arguments_are_tool_errors(mcp_client):
    bad_area = await call(mcp_client, "get_reports_in_area", min_lng=19, min_lat=50, max_lng=18, max_lat=51)
    assert bad_area.is_error and "Niepoprawny obszar" in bad_area.content[0].text
    bad_id = await call(mcp_client, "get_report", id="nie-uuid")
    assert bad_id.is_error


def test_mcp_endpoint_is_mounted(client):
    r = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
        # SDK chroni przed DNS rebinding: akceptuje tylko Host z localhost.
        headers={"Accept": "application/json, text/event-stream", "Host": "localhost:8000"},
    )
    assert r.status_code == 200, r.text
    assert "get_reports_in_area" in r.text
