"""Пользователи: один аккаунт на Telegram ID для бота и Mini App."""
from __future__ import annotations

from ..db import Database, now
from ..errors import DomainError
from . import credits, events, orders, site_settings, sources


def upsert_user(
    db: Database, tg_id: int, username: str | None, first_name: str | None, *,
    last_name: str | None = None, language_code: str | None = None, photo_url: str | None = None,
    start_param: str | None = None,
) -> dict:
    """Создать/обновить пользователя и отметить его активность за сегодня (для DAU/WAU/MAU и удержания)."""
    ts = now()
    with db.tx() as conn:
        existed = conn.execute("SELECT source FROM users WHERE tg_id = ?", (tg_id,)).fetchone()
        src = sources.parse_start_param(start_param, conn, tg_id)
        if existed is None:
            conn.execute(
                "INSERT INTO users (tg_id, username, first_name, last_name, language_code, photo_url, source, campaign, material, "
                "referrer_id, created_at, last_seen_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (tg_id, username, first_name, last_name, language_code, photo_url, src.get("source"), src.get("campaign"),
                 src.get("material"), src.get("referrer_id"), ts, ts),
            )
        else:
            conn.execute(
                "UPDATE users SET username = ?, first_name = ?, last_name = COALESCE(?, last_name), "
                "language_code = COALESCE(?, language_code), photo_url = COALESCE(?, photo_url), last_seen_at = ? WHERE tg_id = ?",
                (username, first_name, last_name, language_code, photo_url, ts, tg_id),
            )
            if src and existed["source"] is None:  # источник проставляется один раз
                conn.execute("UPDATE users SET source = ?, campaign = ?, material = ?, referrer_id = COALESCE(referrer_id, ?) WHERE tg_id = ?",
                             (src.get("source"), src.get("campaign"), src.get("material"), src.get("referrer_id"), tg_id))
        conn.execute("INSERT OR IGNORE INTO daily_activity (day, user_id) VALUES (?, ?)", (ts[:10], tg_id))
        row = dict(conn.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,)).fetchone())
    row["is_new"] = existed is None
    return row


def register(db: Database, tg_id: int) -> tuple[dict, bool]:
    """Вход через Telegram: аккаунт активируется, по желанию начисляется стартовый бонус. Повторный вызов безопасен."""
    with db.tx() as conn:
        u = conn.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,)).fetchone()
        if u is None:
            raise DomainError("Пользователь не найден", code="unknown_user", status=404)
        if u["registered_at"]:
            return dict(u), False
        conn.execute("UPDATE users SET registered_at = ? WHERE tg_id = ?", (now(), tg_id))
        bonus = site_settings.get_int(conn, "welcome_bonus", 0)
        if bonus > 0:
            credits.apply(conn, tg_id, bonus, "welcome_bonus", note="Стартовый бонус")
        events.log_conn(conn, "user_registered", tg_id, source=u["source"], bonus=bonus)
        return dict(conn.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,)).fetchone()), True


def mark_welcomed(db: Database, tg_id: int) -> None:
    with db.tx() as conn:
        conn.execute("UPDATE users SET welcomed = 1 WHERE tg_id = ?", (tg_id,))


def get_user(db: Database, tg_id: int) -> dict | None:
    with db.read() as conn:
        row = conn.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,)).fetchone()
    return dict(row) if row else None


def profile(db: Database, tg_id: int) -> dict:
    user = get_user(db, tg_id) or {}
    return {
        "id": tg_id,
        "first_name": user.get("first_name"),
        "username": user.get("username"),
        "balance": user.get("balance", 0),
        "notify_chat": bool(user.get("notify_chat", 1)),
        "is_pro": bool(user.get("is_pro", 0)),
        "registered": bool(user.get("registered_at")),
        "welcomed": bool(user.get("welcomed", 0)),
        "status": user.get("status", "active"),
        "photo_url": user.get("photo_url"),
        "created_at": user.get("created_at"),
        "free": orders.free_status(db, tg_id),
    }


def set_notify_chat(db: Database, tg_id: int, on: bool) -> None:
    with db.tx() as conn:
        conn.execute("UPDATE users SET notify_chat = ? WHERE tg_id = ?", (int(on), tg_id))


def set_pro(db: Database, tg_id: int, on: bool) -> None:
    """PRO — отметка, которую владелец ставит вручную (оплаты и особых возможностей PRO пока нет)."""
    with db.tx() as conn:
        cur = conn.execute("UPDATE users SET is_pro = ? WHERE tg_id = ?", (int(on), tg_id))
        if cur.rowcount == 0:
            raise DomainError("Пользователь не найден", code="unknown_user", status=404)
        events.log_conn(conn, "pro_enabled" if on else "pro_cancelled", tg_id)
