"""Личные токены для подключения MCP-клиентов (ChatGPT, Claude, Cursor, Codex и др.).

Токен показывается ОДИН раз при создании; в базе хранится только его SHA-256. Токен действует от имени пользователя:
списывает его токены и видит только его историю. Любой токен можно отозвать."""
from __future__ import annotations

import hashlib
import secrets

from ..db import Database, now
from ..errors import DomainError

MAX_ACTIVE = 5


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create(db: Database, user_id: int, label: str = "") -> dict:
    with db.tx() as conn:
        n = conn.execute("SELECT COUNT(*) FROM api_tokens WHERE user_id = ? AND revoked_at IS NULL", (user_id,)).fetchone()[0]
        if n >= MAX_ACTIVE:
            raise DomainError(f"Можно иметь не больше {MAX_ACTIVE} активных токенов — отзовите ненужный", code="token_limit")
        token = "nolla_" + secrets.token_urlsafe(32)
        cur = conn.execute("INSERT INTO api_tokens (user_id, token_hash, label, created_at) VALUES (?, ?, ?, ?)",
                           (user_id, _hash(token), (label or "").strip()[:40], now()))
    return {"id": cur.lastrowid, "token": token, "label": (label or "").strip()[:40]}


def list_for_user(db: Database, user_id: int) -> list[dict]:
    with db.read() as conn:
        rows = conn.execute("SELECT id, label, created_at, last_used_at FROM api_tokens WHERE user_id = ? AND revoked_at IS NULL ORDER BY id DESC", (user_id,)).fetchall()
    return [dict(r) for r in rows]


def revoke(db: Database, user_id: int, token_id: int) -> None:
    with db.tx() as conn:
        cur = conn.execute("UPDATE api_tokens SET revoked_at = ? WHERE id = ? AND user_id = ? AND revoked_at IS NULL", (now(), token_id, user_id))
        if cur.rowcount == 0:
            raise DomainError("Токен не найден", code="not_found", status=404)


def authenticate(db: Database, token: str) -> int | None:
    """Возвращает Telegram ID владельца или None. Заблокированные пользователи не проходят."""
    if not token.startswith("nolla_") or len(token) > 100:
        return None
    with db.tx() as conn:
        row = conn.execute(
            "SELECT t.id, t.user_id FROM api_tokens t JOIN users u ON u.tg_id = t.user_id WHERE t.token_hash = ? AND t.revoked_at IS NULL AND u.status != 'blocked'",
            (_hash(token),)).fetchone()
        if row is None:
            return None
        conn.execute("UPDATE api_tokens SET last_used_at = ? WHERE id = ?", (now(), row["id"]))
        return row["user_id"]
