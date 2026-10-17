"""Generowanie obrazków testowych (opcjonalnie z GPS i datą w EXIF)."""

import io
from datetime import datetime

from PIL import Image

from scripts.demo_images import build_exif


def make_image(
    fmt: str = "JPEG",
    size: tuple[int, int] = (1280, 960),
    color: str = "gray",
    gps: tuple[float, float] | None = None,
    taken_at: datetime | None = None,
) -> bytes:
    """gps jako (lng, lat); taken_at jako czas lokalny bez strefy, jak w aparatach."""
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, fmt, exif=build_exif(gps, taken_at))
    return buf.getvalue()
