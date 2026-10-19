"""Файлы на диске: загруженные фото и результаты генерации."""
from __future__ import annotations

import uuid
from pathlib import Path


class Storage:
    def __init__(self, data_dir: str):
        self.root = Path(data_dir)
        self.uploads = self.root / "uploads"
        self.results = self.root / "results"
        self.media = self.root / "media"  # публичные примеры работ, обложки, баннер
        self.uploads.mkdir(parents=True, exist_ok=True)
        self.results.mkdir(parents=True, exist_ok=True)
        self.media.mkdir(parents=True, exist_ok=True)

    def save_upload(self, data: bytes) -> str:
        path = self.uploads / f"{uuid.uuid4().hex}.jpg"
        path.write_bytes(data)
        return str(path)

    def save_result(self, order_id: int, data: bytes, ext: str) -> str:
        path = self.results / f"order_{order_id}_{uuid.uuid4().hex[:6]}.{ext}"
        path.write_bytes(data)
        return str(path)

    def save_media(self, data: bytes, ext: str) -> str:
        name = f"{uuid.uuid4().hex}.{ext}"
        (self.media / name).write_bytes(data)
        return name

    @staticmethod
    def delete(path: str | None) -> None:
        if path:
            try:
                Path(path).unlink(missing_ok=True)
            except OSError:
                pass
