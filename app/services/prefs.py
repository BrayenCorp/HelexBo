"""Настройки пользователя: язык (пока только русский), модель и параметры по умолчанию, автоскачивание, цели из онбординга."""
from __future__ import annotations

import json

from ..db import Database
from ..errors import DomainError
from . import params as P

INTERESTS = {"photo": "Фото", "video": "Видео", "avatars": "Аватары", "social": "Контент для соцсетей", "ads": "Реклама", "other": "Другое"}
DEFAULTS = {"language": "ru", "default_model_id": None, "ratio": "1:1", "quality": "standard", "autodownload": False, "interests": []}


def get(db: Database, user_id: int) -> dict:
    with db.read() as conn:
        row = conn.execute("SELECT prefs, notify_chat FROM users WHERE tg_id = ?", (user_id,)).fetchone()
    try:
        data = json.loads(row["prefs"] or "{}") if row else {}
    except ValueError:
        data = {}
    out = {**DEFAULTS, **{k: v for k, v in data.items() if k in DEFAULTS}}
    out["notify"] = bool(row["notify_chat"]) if row else True
    return out


def update(db: Database, user_id: int, fields: dict) -> dict:
    cur = get(db, user_id)
    cur.pop("notify", None)
    if "ratio" in fields:
        if fields["ratio"] not in P.FORMATS:
            raise DomainError("Недопустимое соотношение сторон")
        cur["ratio"] = fields["ratio"]
    if "quality" in fields:
        if fields["quality"] not in P.QUALITIES:
            raise DomainError("Недопустимое качество")
        cur["quality"] = fields["quality"]
    if "autodownload" in fields:
        cur["autodownload"] = bool(fields["autodownload"])
    if "default_model_id" in fields:
        mid = fields["default_model_id"]
        if mid in (None, ""):
            cur["default_model_id"] = None
        else:
            with db.read() as conn:
                ok = conn.execute("SELECT 1 FROM ai_models WHERE id = ? AND is_active = 1 AND kind = 'photo'", (int(mid),)).fetchone()
            if ok is None:
                raise DomainError("Эта модель недоступна")
            cur["default_model_id"] = int(mid)
    if "interests" in fields:
        items = fields["interests"]
        if not isinstance(items, list) or any(i not in INTERESTS for i in items):
            raise DomainError("Недопустимый выбор")
        cur["interests"] = items
    with db.tx() as conn:
        conn.execute("UPDATE users SET prefs = ? WHERE tg_id = ?", (json.dumps(cur, ensure_ascii=False), user_id))
        if "notify" in fields:
            conn.execute("UPDATE users SET notify_chat = ? WHERE tg_id = ?", (int(bool(fields["notify"])), user_id))
    return get(db, user_id)
