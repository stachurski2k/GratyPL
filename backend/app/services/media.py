"""Zdjęcia: walidacja, zapis na dysk, miniatury i odczyt EXIF (data, GPS)."""

import io
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone

from PIL import ExifTags, Image, ImageOps, UnidentifiedImageError

from app.config import WARSAW, settings
from app.services.errors import InvalidInput

MAX_PHOTO_BYTES = 10 * 1024 * 1024
THUMB_SIZE = 480
ALLOWED_FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}


@dataclass
class PhotoUpload:
    """Surowe zdjęcie z dowolnego źródła (upload HTTP, seeder)."""

    filename: str
    data: bytes


@dataclass
class ParsedPhoto:
    data: bytes
    extension: str
    taken_at: datetime | None
    gps: tuple[float, float] | None  # (lng, lat)


@dataclass
class StoredPhoto:
    path: str
    thumb_path: str


def media_url(path: str) -> str:
    return f"/media/{path}"


def parse_photo(upload: PhotoUpload) -> ParsedPhoto:
    name = upload.filename or "zdjęcie"
    if len(upload.data) > MAX_PHOTO_BYTES:
        raise InvalidInput(f"Plik {name} jest za duży (maks. 10 MB).")
    try:
        with Image.open(io.BytesIO(upload.data)) as img:
            fmt = img.format
            img.verify()
        with Image.open(io.BytesIO(upload.data)) as img:
            img.load()  # PNG trzyma EXIF w chunku, który Pillow czyta dopiero po load()
            exif = img.getexif()
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise InvalidInput(f"Plik {name} nie jest poprawnym obrazem.") from None
    if fmt not in ALLOWED_FORMATS:
        raise InvalidInput(f"Plik {name}: dozwolone formaty to JPEG, PNG i WebP.")
    return ParsedPhoto(
        data=upload.data,
        extension=ALLOWED_FORMATS[fmt],
        taken_at=_exif_taken_at(exif),
        gps=_exif_gps(exif),
    )


def store_photo(photo: ParsedPhoto, directory: str, stem: str) -> StoredPhoto:
    """Zapisuje oryginał i miniaturę JPEG w MEDIA_ROOT/{directory}/."""
    target = settings.media_root / directory
    target.mkdir(parents=True, exist_ok=True)
    path = f"{directory}/{stem}.{photo.extension}"
    thumb_path = f"{directory}/{stem}_thumb.jpg"
    (settings.media_root / path).write_bytes(photo.data)
    with Image.open(io.BytesIO(photo.data)) as img:
        thumb = ImageOps.exif_transpose(img).convert("RGB")
        thumb.thumbnail((THUMB_SIZE, THUMB_SIZE))
        thumb.save(settings.media_root / thumb_path, "JPEG", quality=85)
    return StoredPhoto(path=path, thumb_path=thumb_path)


def copy_file(src: str, dest: str) -> None:
    """Kopiuje plik w obrębie MEDIA_ROOT (ścieżki względne)."""
    target = settings.media_root / dest
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(settings.media_root / src, target)


def remove_dir(directory: str) -> None:
    shutil.rmtree(settings.media_root / directory, ignore_errors=True)


def _exif_taken_at(exif: Image.Exif) -> datetime | None:
    ifd = exif.get_ifd(ExifTags.IFD.Exif)
    raw = ifd.get(ExifTags.Base.DateTimeOriginal) or exif.get(ExifTags.Base.DateTime)
    if not raw:
        return None
    try:
        naive = datetime.strptime(str(raw).strip("\x00 "), "%Y:%m:%d %H:%M:%S")
    except ValueError:
        return None
    offset = ifd.get(ExifTags.Base.OffsetTimeOriginal)
    if offset:
        try:
            aware = datetime.strptime(f"{naive:%Y-%m-%d %H:%M:%S} {offset}", "%Y-%m-%d %H:%M:%S %z")
            return aware.astimezone(timezone.utc)
        except ValueError:
            pass
    # Bez strefy w EXIF zakładamy czas lokalny (Polska).
    return naive.replace(tzinfo=WARSAW).astimezone(timezone.utc)


def _exif_gps(exif: Image.Exif) -> tuple[float, float] | None:
    gps = exif.get_ifd(ExifTags.IFD.GPSInfo)
    try:
        lat = _dms_to_degrees(gps[ExifTags.GPS.GPSLatitude])
        lng = _dms_to_degrees(gps[ExifTags.GPS.GPSLongitude])
        if gps.get(ExifTags.GPS.GPSLatitudeRef, "N") == "S":
            lat = -lat
        if gps.get(ExifTags.GPS.GPSLongitudeRef, "E") == "W":
            lng = -lng
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return None
    if not (-180 <= lng <= 180 and -90 <= lat <= 90) or (lng == 0 and lat == 0):
        return None
    return (lng, lat)


def _dms_to_degrees(dms) -> float:
    d, m, s = (float(x) for x in dms)
    return round(d + m / 60 + s / 3600, 7)  # ~1 cm; usuwa szum zmiennoprzecinkowy
