"""Generowanie obrazków testowych (opcjonalnie z GPS i datą w EXIF)."""

import io
from datetime import datetime

from PIL import ExifTags, Image


def _dms(value: float) -> tuple[float, float, float]:
    value = abs(value)
    d = int(value)
    m = int((value - d) * 60)
    s = round((value - d - m / 60) * 3600, 4)
    return (d, m, s)


def make_image(
    fmt: str = "JPEG",
    size: tuple[int, int] = (1280, 960),
    color: str = "gray",
    gps: tuple[float, float] | None = None,
    taken_at: datetime | None = None,
) -> bytes:
    """gps jako (lng, lat); taken_at jako czas lokalny bez strefy, jak w aparatach."""
    img = Image.new("RGB", size, color)
    exif = Image.Exif()
    if gps is not None:
        lng, lat = gps
        gps_ifd = exif.get_ifd(ExifTags.IFD.GPSInfo)
        gps_ifd[ExifTags.GPS.GPSLatitudeRef] = "N" if lat >= 0 else "S"
        gps_ifd[ExifTags.GPS.GPSLatitude] = _dms(lat)
        gps_ifd[ExifTags.GPS.GPSLongitudeRef] = "E" if lng >= 0 else "W"
        gps_ifd[ExifTags.GPS.GPSLongitude] = _dms(lng)
    if taken_at is not None:
        exif.get_ifd(ExifTags.IFD.Exif)[ExifTags.Base.DateTimeOriginal] = taken_at.strftime(
            "%Y:%m:%d %H:%M:%S"
        )
    buf = io.BytesIO()
    img.save(buf, fmt, exif=exif.tobytes())
    return buf.getvalue()
