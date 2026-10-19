"""Загрузка собственных фото и видео владельцем (обложки, превью, витрина, баннер)."""
from __future__ import annotations

from ..errors import InvalidImage
from ..storage import Storage
from .images import sanitize_image

MP4_BRANDS_OK = True


def detect_video(data: bytes) -> str | None:
    if len(data) > 12 and data[4:8] == b"ftyp":
        return "mp4"
    if data[:4] == b"\x1a\x45\xdf\xa3":
        return "webm"
    return None


def save_media(storage: Storage, data: bytes, *, max_image: int, max_video: int) -> dict:
    """Принимает JPEG/PNG/WEBP или MP4/WEBM. Возвращает публичный адрес файла."""
    if not data:
        raise InvalidImage("Файл пустой")
    ext = detect_video(data)
    if ext:
        if len(data) > max_video:
            raise InvalidImage(f"Видео больше {max_video // 1024 // 1024} МБ — сожмите его или сократите")
        return {"url": f"/media/{storage.save_media(data, ext)}", "kind": "video"}
    clean = sanitize_image(data, max_image, max_side=1800)
    return {"url": f"/media/{storage.save_media(clean, 'jpg')}", "kind": "image"}
