"""Тексты главной (баннер, карточка AI-видео) и ссылка на поддержку — редактируются в админ-панели."""
from __future__ import annotations

from ..db import Database

EDITABLE = {
    "banner_title": 120, "banner_text": 300, "banner_button": 40, "banner_image_url": 500,
    "video_title": 80, "video_text": 160, "video_image_url": 500,
    "support_url": 300,
    "welcome_bonus": 9,
    "max_variants": 2,
    "ideas_channel_url": 300,   # канал с идеями и промптами: кнопка «Посмотреть идеи» в боте
    "referral_bonus": 9,        # сколько токенов получает пригласивший, когда друг входит
}


def get_all(db: Database) -> dict:
    with db.read() as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
    data = {r["key"]: r["value"] for r in rows}
    return {k: data.get(k, "") for k in EDITABLE}


def update(db: Database, fields: dict) -> dict:
    from ..errors import DomainError

    for key in ("welcome_bonus", "max_variants", "referral_bonus"):
        if key in fields:
            v = str(fields[key]).strip()
            if not v.isdigit() or (key == "max_variants" and not 1 <= int(v) <= 8) or (key in ("welcome_bonus", "referral_bonus") and int(v) > 100000):
                raise DomainError("Бонусы — целое число токенов (0 — выключено), число вариантов — от 1 до 8")
    with db.tx() as conn:
        for key, limit in EDITABLE.items():
            if key in fields:
                conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(fields[key]).strip()[:limit]))
    return get_all(db)


def set_value(db: Database, key: str, value: str) -> None:
    """Служебная запись (не из админки): отметка сборки бота и подобное."""
    with db.tx() as conn:
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)[:300]))


def get_value(db: Database, key: str, default: str = "") -> str:
    with db.read() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def get_int(conn, key: str, default: int = 0) -> int:
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    try:
        return int(row["value"]) if row else default
    except (TypeError, ValueError):
        return default
