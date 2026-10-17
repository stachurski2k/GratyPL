import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas import BBox, Point, ReportOut, feature_collection
from app.services import reports
from app.services.errors import InvalidInput
from app.services.media import MAX_PHOTO_BYTES, PhotoUpload

router = APIRouter(prefix="/api/reports", tags=["reports"])
SessionDep = Annotated[Session, Depends(get_session)]


@router.post("", status_code=201)
def create_report(
    session: SessionDep,
    photos: Annotated[list[UploadFile], File(description="1–5 zdjęć (JPEG/PNG/WebP, maks. 10 MB)")],
    lng: Annotated[float | None, Form()] = None,
    lat: Annotated[float | None, Form()] = None,
    description: Annotated[str | None, Form()] = None,
    has_plates: Annotated[bool | None, Form()] = None,
) -> ReportOut:
    if (lng is None) != (lat is None):
        raise InvalidInput("Podaj obie współrzędne (lng i lat) albo żadnej.")
    try:
        location = Point(lng=lng, lat=lat) if lng is not None else None
    except ValueError:
        raise InvalidInput("Współrzędne poza zakresem.") from None
    # Czytamy o bajt więcej niż limit, żeby serwis wykrył za duży plik bez wczytywania całości.
    uploads = [PhotoUpload(filename=f.filename or "", data=f.file.read(MAX_PHOTO_BYTES + 1)) for f in photos]
    report = reports.create_report(
        session, uploads, location=location, description=description, has_plates=has_plates
    )
    return ReportOut.from_model(report)


@router.get("/geojson")
def reports_geojson(
    session: SessionDep,
    bbox: Annotated[str, Query(description="minLng,minLat,maxLng,maxLat", examples=["18.5,50.2,18.9,50.4"])],
) -> dict:
    try:
        area = BBox.parse(bbox)
    except ValueError as e:
        raise InvalidInput(str(e)) from None
    return feature_collection(reports.reports_in_area(session, area))


@router.get("/{report_id}")
def get_report(session: SessionDep, report_id: uuid.UUID) -> ReportOut:
    return ReportOut.from_model(reports.get_report(session, report_id))


@router.delete("/{report_id}", status_code=204)
def delete_report(session: SessionDep, report_id: uuid.UUID) -> Response:
    reports.delete_report(session, report_id)
    return Response(status_code=204)
