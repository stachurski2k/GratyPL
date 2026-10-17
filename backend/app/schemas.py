"""Formaty wejścia/wyjścia API i MCP.

To jedyne miejsce, które definiuje format współrzędnych: zawsze GeoJSON/PostGIS,
czyli [lng, lat] w WGS84 (SRID 4326).
"""

import uuid
from datetime import date, datetime, timedelta
from typing import Annotated, Literal

from pydantic import BaseModel, Field, ValidationError, model_validator

from app.models import Report, WeeklySummary
from app.services.media import media_url

LngLat = Annotated[
    tuple[float, float], Field(description="Współrzędne [lng, lat], WGS84 (SRID 4326)")
]


class Point(BaseModel):
    lng: float = Field(ge=-180, le=180)
    lat: float = Field(ge=-90, le=90)

    def as_lnglat(self) -> tuple[float, float]:
        return (self.lng, self.lat)

    def to_ewkt(self) -> str:
        return f"SRID=4326;POINT({self.lng} {self.lat})"


class BBox(BaseModel):
    """Prostokąt [minLng, minLat, maxLng, maxLat]."""

    min_lng: float = Field(ge=-180, le=180)
    min_lat: float = Field(ge=-90, le=90)
    max_lng: float = Field(ge=-180, le=180)
    max_lat: float = Field(ge=-90, le=90)

    @model_validator(mode="after")
    def _check_order(self) -> "BBox":
        if self.min_lng >= self.max_lng or self.min_lat >= self.max_lat:
            raise ValueError("bbox: wymagane minLng < maxLng i minLat < maxLat")
        return self

    @classmethod
    def parse(cls, value: str) -> "BBox":
        """Parsuje 'minLng,minLat,maxLng,maxLat' (ValueError przy złym formacie)."""
        parts = value.split(",")
        if len(parts) != 4:
            raise ValueError("bbox: oczekiwano 4 liczb 'minLng,minLat,maxLng,maxLat'")
        try:
            min_lng, min_lat, max_lng, max_lat = (float(p) for p in parts)
        except ValueError:
            raise ValueError("bbox: wartości muszą być liczbami") from None
        try:
            return cls(min_lng=min_lng, min_lat=min_lat, max_lng=max_lng, max_lat=max_lat)
        except ValidationError:
            raise ValueError(
                "bbox: współrzędne poza zakresem albo minLng >= maxLng / minLat >= maxLat"
            ) from None

    def as_list(self) -> list[float]:
        return [self.min_lng, self.min_lat, self.max_lng, self.max_lat]


class PhotoOut(BaseModel):
    url: str
    thumb_url: str
    taken_at: datetime | None


class ReportOut(BaseModel):
    id: uuid.UUID
    created_at: datetime
    location: LngLat
    description: str | None
    has_plates: bool | None
    source: Literal["web", "seed"]
    photos: list[PhotoOut]

    @classmethod
    def from_model(cls, report: Report) -> "ReportOut":
        return cls(
            id=report.id,
            created_at=report.created_at,
            location=(report.lng, report.lat),
            description=report.description,
            has_plates=report.has_plates,
            source=report.source,
            photos=[
                PhotoOut(url=media_url(p.path), thumb_url=media_url(p.thumb_path), taken_at=p.taken_at)
                for p in report.photos
            ],
        )


class SnapshotReportOut(BaseModel):
    id: uuid.UUID
    created_at: datetime
    location: LngLat
    description: str | None
    has_plates: bool | None
    thumb_urls: list[str]


class SummaryOut(BaseModel):
    id: uuid.UUID
    week_start: date
    week_end: date = Field(description="Pierwszy dzień po tygodniu (zakres [week_start, week_end))")
    generated_at: datetime
    report_count: int
    bbox: list[float] | None = Field(description="[minLng, minLat, maxLng, maxLat]")
    reports: list[SnapshotReportOut]

    @classmethod
    def from_model(cls, summary: WeeklySummary) -> "SummaryOut":
        return cls(
            id=summary.id,
            week_start=summary.week_start,
            week_end=summary.week_start + timedelta(days=7),
            generated_at=summary.generated_at,
            report_count=summary.report_count,
            bbox=summary.bbox,
            reports=[
                SnapshotReportOut(
                    id=item["id"],
                    created_at=item["created_at"],
                    location=tuple(item["location"]),
                    description=item["description"],
                    has_plates=item["has_plates"],
                    thumb_urls=[media_url(t) for t in item["thumbs"]],
                )
                for item in summary.snapshot
            ],
        )


class FeedReport(ReportOut):
    type: Literal["report"] = "report"


class FeedSummary(SummaryOut):
    type: Literal["summary"] = "summary"


class FeedPage(BaseModel):
    items: list[Annotated[FeedReport | FeedSummary, Field(discriminator="type")]]
    next_cursor: str | None


def feed_item(obj: Report | WeeklySummary) -> FeedReport | FeedSummary:
    if isinstance(obj, Report):
        return FeedReport(**ReportOut.from_model(obj).model_dump())
    return FeedSummary(**SummaryOut.from_model(obj).model_dump())


def report_feature(report: Report) -> dict:
    """Zgłoszenie jako GeoJSON Feature (lekkie właściwości do mapy)."""
    return {
        "type": "Feature",
        "id": str(report.id),
        "geometry": {"type": "Point", "coordinates": [report.lng, report.lat]},
        "properties": {
            "id": str(report.id),
            "created_at": report.created_at.isoformat(),
            "description": report.description,
            "has_plates": report.has_plates,
            "source": report.source,
            "thumb_url": media_url(report.photos[0].thumb_path) if report.photos else None,
        },
    }


def feature_collection(reports: list[Report]) -> dict:
    return {"type": "FeatureCollection", "features": [report_feature(r) for r in reports]}
