"""Аватары: цифровая версия человека для будущих сцен.

Пользователь подтверждает право использовать фотографии и загружает 3–25 фото (рекомендуем 10–25). Фото лежат в файлах на сервере
и удаляются вместе с аватаром или кнопкой «Удалить мои фото и работы». В ДЕМО-режиме «обучения» нет: этапы
«Анализ внешности» → «Создание аватара» только имитируются, а сцены строятся от обложки аватара. Настоящее обучение подключается в
провайдере (app/ai/external.py) — пока AI_MODE=live без него создание аватара честно завершается ошибкой."""
from __future__ import annotations

import io
import json
import time
import uuid
from pathlib import Path

from PIL import Image, ImageOps

from ..db import Database, now
from ..errors import DomainError
from ..storage import Storage
from .images import sanitize_image

MIN_PHOTOS, MAX_PHOTOS, MAX_AVATARS = 3, 25, 5
STATUS_LABELS = {"queued": "В очереди", "analyzing": "Анализ внешности", "creating": "Создание аватара", "ready": "Аватар готов", "failed": "Ошибка"}


def public(a: dict) -> dict:
    return {"id": a["id"], "name": a["name"], "status": a["status"], "status_label": STATUS_LABELS.get(a["status"], a["status"]),
            "photo_count": a["photo_count"], "has_cover": bool(a["cover_path"]) and a["status"] == "ready", "created_at": a["created_at"],
            "is_stub": bool(a["is_stub"]), "error": a["error"] if a["status"] == "failed" else None}


def list_for_user(db: Database, user_id: int) -> list[dict]:
    with db.read() as conn:
        rows = conn.execute("SELECT * FROM avatars WHERE user_id = ? ORDER BY id DESC", (user_id,)).fetchall()
    return [public(dict(r)) for r in rows]


def get_owned(db: Database, user_id: int, avatar_id: int) -> dict:
    with db.read() as conn:
        row = conn.execute("SELECT * FROM avatars WHERE id = ? AND user_id = ?", (avatar_id, user_id)).fetchone()
    if row is None:
        raise DomainError("Аватар не найден", code="not_found", status=404)
    return dict(row)


def create(db: Database, storage: Storage, user_id: int, name: str, photos: list[bytes], consent: bool, max_bytes: int) -> dict:
    name = (name or "").strip()[:40] or "Мой аватар"
    if not consent:
        raise DomainError("Подтвердите, что у вас есть право использовать эти фотографии", code="consent_required")
    if len(photos) < MIN_PHOTOS:
        raise DomainError(f"Загрузите минимум {MIN_PHOTOS} фотографии (лучше 10–25)", code="not_enough_photos")
    if len(photos) > MAX_PHOTOS:
        raise DomainError(f"Не больше {MAX_PHOTOS} фотографий", code="too_many_photos")
    clean = [sanitize_image(p, max_bytes) for p in photos]
    folder = storage.root / "avatars"
    folder.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    try:
        for data in clean:
            path = folder / f"{uuid.uuid4().hex}.jpg"
            path.write_bytes(data)
            paths.append(str(path))
        with Image.open(io.BytesIO(clean[0])) as im:
            cover = ImageOps.fit(im.convert("RGB"), (768, 768))
        cover_path = folder / f"{uuid.uuid4().hex}_cover.jpg"
        buf = io.BytesIO()
        cover.save(buf, "JPEG", quality=90)
        cover_path.write_bytes(buf.getvalue())
        paths.append(str(cover_path))
        with db.tx() as conn:
            n = conn.execute("SELECT COUNT(*) FROM avatars WHERE user_id = ?", (user_id,)).fetchone()[0]
            if n >= MAX_AVATARS:
                raise DomainError(f"Можно хранить не больше {MAX_AVATARS} аватаров — удалите ненужный", code="avatar_limit")
            cur = conn.execute(
                "INSERT INTO avatars (user_id, name, status, photo_count, photos, cover_path, created_at) VALUES (?, ?, 'queued', ?, ?, ?, ?)",
                (user_id, name, len(clean), json.dumps(paths[:-1]), str(cover_path), now()))
            row = dict(conn.execute("SELECT * FROM avatars WHERE id = ?", (cur.lastrowid,)).fetchone())
    except BaseException:
        for p in paths:
            storage.delete(p)
        raise
    return row


def _set(db: Database, avatar_id: int, **fields) -> None:
    with db.tx() as conn:
        conn.execute(f"UPDATE avatars SET {', '.join(f'{k} = ?' for k in fields)} WHERE id = ? AND status != 'ready'", [*fields.values(), avatar_id])


def process(db: Database, storage: Storage, ai_mode: str, avatar_id: int, delay: float = 0.0) -> None:
    """Этапы создания аватара. В демо-режиме имитируются; в live без провайдера — ошибка."""
    if ai_mode != "mock":
        _set(db, avatar_id, status="failed", error="Создание аватаров ещё не подключено к провайдеру. Фотографии не используются.")
        return
    _set(db, avatar_id, status="analyzing", is_stub=1)
    time.sleep(delay)
    _set(db, avatar_id, status="creating")
    time.sleep(delay)
    _set(db, avatar_id, status="ready", ready_at=now())


def fail_unfinished(db: Database) -> int:
    with db.tx() as conn:
        return conn.execute("UPDATE avatars SET status = 'failed', error = 'Сервис был перезапущен во время создания. Создайте аватар заново.' "
                            "WHERE status IN ('queued', 'analyzing', 'creating')").rowcount


def _files(a: dict) -> list[str]:
    try:
        paths = json.loads(a.get("photos") or "[]")
    except ValueError:
        paths = []
    return [*paths, a.get("cover_path")]


def delete(db: Database, storage: Storage, user_id: int, avatar_id: int) -> None:
    a = get_owned(db, user_id, avatar_id)
    with db.tx() as conn:
        conn.execute("DELETE FROM avatars WHERE id = ? AND user_id = ?", (avatar_id, user_id))
    for p in _files(a):
        storage.delete(p)


def delete_all(db: Database, storage: Storage, user_id: int) -> int:
    with db.tx() as conn:
        rows = [dict(r) for r in conn.execute("SELECT * FROM avatars WHERE user_id = ?", (user_id,))]
        conn.execute("DELETE FROM avatars WHERE user_id = ?", (user_id,))
    for a in rows:
        for p in _files(a):
            storage.delete(p)
    return len(rows)


def cover_file(db: Database, user_id: int, avatar_id: int) -> str:
    a = get_owned(db, user_id, avatar_id)
    if a["status"] != "ready" or not a["cover_path"] or not Path(a["cover_path"]).exists():
        raise DomainError("Обложки нет", code="not_found", status=404)
    return a["cover_path"]
