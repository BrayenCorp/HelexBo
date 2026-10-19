"""Ваши фото для обложек карточек.

Положите любые изображения в папку data/media/previews (или загрузите их в админке).
Интерфейс сам расставит их по карточкам, у которых нет собственной обложки: каждая карточка
всегда получает одно и то же фото (по своему номеру), поэтому обложки не «прыгают» при обновлении.
"""
from __future__ import annotations

from pathlib import Path

from ..errors import DomainError
from ..storage import Storage
from .images import sanitize_image

EXTS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_FILES = 200


def _files(storage: Storage) -> list[Path]:
    if not storage.previews.is_dir():
        return []
    return sorted((p for p in storage.previews.iterdir() if p.is_file() and p.suffix.lower() in EXTS), key=lambda p: p.name)


def list_public(storage: Storage) -> list[str]:
    """Адреса фото для интерфейса. Пусто — интерфейс покажет нейтральные плашки."""
    return [f"/media/previews/{p.name}" for p in _files(storage)]


def list_admin(storage: Storage) -> list[dict]:
    return [{"name": p.name, "url": f"/media/previews/{p.name}", "size": p.stat().st_size} for p in _files(storage)]


def save(storage: Storage, data: bytes, max_bytes: int) -> dict:
    if len(_files(storage)) >= MAX_FILES:
        raise DomainError(f"Больше {MAX_FILES} фото не нужно — удалите лишние")
    if not data:
        raise DomainError("Пустой файл")
    if len(data) > max_bytes:
        raise DomainError("Файл слишком большой")
    name = storage.save_preview(sanitize_image(data, max_bytes, max_side=1600))
    return {"name": name, "url": f"/media/previews/{name}"}


def delete(storage: Storage, name: str) -> None:
    safe = Path(name).name
    target = storage.previews / safe
    if not target.is_file():
        raise DomainError("Файл не найден", code="not_found", status=404)
    target.unlink(missing_ok=True)
