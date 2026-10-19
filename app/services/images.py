"""Проверка и очистка загруженных фото: формат, размер, EXIF (геометки) вырезаются."""
from __future__ import annotations

import io

from PIL import Image, ImageOps, UnidentifiedImageError

from ..errors import InvalidImage

Image.MAX_IMAGE_PIXELS = 40_000_000
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


def sanitize_image(data: bytes, max_bytes: int, max_side: int = 2048) -> bytes:
    if not data:
        raise InvalidImage("Файл пустой")
    if len(data) > max_bytes:
        raise InvalidImage(f"Файл слишком большой (максимум {max_bytes // 1024 // 1024} МБ)")
    try:
        with Image.open(io.BytesIO(data)) as im:
            if im.format not in ALLOWED_FORMATS:
                raise InvalidImage("Поддерживаются только JPEG, PNG и WEBP")
            im.load()
            fixed = ImageOps.exif_transpose(im)
            rgb = fixed.convert("RGB")
    except InvalidImage:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise InvalidImage("Не удалось прочитать изображение — пришлите обычное фото")
    if min(rgb.size) < 64:
        raise InvalidImage("Фото слишком маленькое")
    rgb.thumbnail((max_side, max_side))
    out = io.BytesIO()
    rgb.save(out, "JPEG", quality=90)
    return out.getvalue()
