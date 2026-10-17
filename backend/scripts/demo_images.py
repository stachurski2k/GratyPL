"""Zastępcze obrazki do danych demo: sylwetka auta bez kół, napis DEMO, opcjonalnie EXIF."""

import io
import random
from datetime import datetime

from PIL import ExifTags, Image, ImageDraw, ImageFont

SIZE = (1280, 960)
BACKGROUNDS = [(176, 190, 197), (200, 194, 180), (168, 184, 160), (190, 180, 186)]
CAR_COLORS = [(120, 40, 40), (40, 70, 120), (60, 60, 60), (150, 150, 150), (30, 90, 60), (170, 120, 40)]


def _dms(value: float) -> tuple[float, float, float]:
    value = abs(value)
    d = int(value)
    m = int((value - d) * 60)
    s = round((value - d - m / 60) * 3600, 4)
    return (d, m, s)


def build_exif(gps: tuple[float, float] | None = None, taken_at: datetime | None = None) -> bytes:
    """EXIF z GPS (lng, lat) i datą zrobienia (czas lokalny bez strefy, jak w aparatach)."""
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
    return exif.tobytes()


def demo_car_jpeg(
    number: int,
    rng: random.Random,
    gps: tuple[float, float] | None = None,
    taken_at: datetime | None = None,
) -> bytes:
    """Obrazek JPEG 1280×960: auto bez kół na jednolitym tle, z napisem DEMO i numerem zgłoszenia."""
    bg = tuple(max(0, min(255, c + rng.randint(-12, 12))) for c in rng.choice(BACKGROUNDS))
    img = Image.new("RGB", SIZE, bg)
    draw = ImageDraw.Draw(img)
    w, h = SIZE

    ground = int(h * 0.72)
    draw.rectangle([0, ground, w, h], fill=tuple(int(c * 0.7) for c in bg))

    # Karoseria: dolna bryła + kabina, przesunięte losowo.
    car = rng.choice(CAR_COLORS)
    x0 = rng.randint(140, 300)
    length = rng.randint(720, 820)
    body_top = ground - rng.randint(170, 200)
    body_bottom = ground - 60  # auto stoi na „cegłach”, nie na kołach
    draw.rounded_rectangle([x0, body_top, x0 + length, body_bottom], radius=30, fill=car)
    cabin_l, cabin_r = x0 + int(length * 0.22), x0 + int(length * 0.72)
    cabin_top = body_top - rng.randint(110, 140)
    draw.polygon(
        [(cabin_l, body_top), (cabin_l + 70, cabin_top), (cabin_r - 50, cabin_top), (cabin_r + 40, body_top)],
        fill=car,
    )
    glass = (90, 110, 125)
    draw.polygon(
        [(cabin_l + 25, body_top - 8), (cabin_l + 80, cabin_top + 15),
         (cabin_r - 60, cabin_top + 15), (cabin_r + 15, body_top - 8)],
        fill=glass,
    )
    # Puste nadkola i cegły zamiast kół.
    for cx in (x0 + int(length * 0.2), x0 + int(length * 0.8)):
        draw.chord([cx - 75, body_bottom - 75, cx + 75, body_bottom + 75], 180, 360, fill=bg)
        draw.rectangle([cx - 45, body_bottom, cx + 45, ground], fill=(150, 70, 50), outline=(90, 40, 30), width=3)

    big = ImageFont.load_default(size=220)
    small = ImageFont.load_default(size=56)
    draw.text((w / 2, 40), "DEMO", font=big, fill=(200, 30, 30), anchor="mt", stroke_width=6, stroke_fill="white")
    # Wbudowany font Pillow nie ma polskich znaków, stąd tekst bez diakrytyków.
    draw.text(
        (w / 2, h - 40),
        f"Dane demo - nr {number}",
        font=small,
        fill="white",
        anchor="mb",
        stroke_width=3,
        stroke_fill="black",
    )

    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85, exif=build_exif(gps, taken_at))
    return buf.getvalue()
