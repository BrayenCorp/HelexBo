"""Кредиты: единый журнал операций. Баланс меняется только здесь и только вместе с записью в журнале."""
from __future__ import annotations

import sqlite3

from ..db import Database, now
from ..errors import DomainError, DuplicateOperation, InsufficientCredits


def apply(
    conn: sqlite3.Connection,
    user_id: int,
    delta: int,
    reason: str,
    *,
    order_id: int | None = None,
    payment_id: int | None = None,
    note: str | None = None,
) -> None:
    """Изменить баланс внутри уже открытой транзакции.

    Уникальные индексы (order_id, reason) и (payment_id, reason) не дают провести
    одну и ту же операцию дважды: повторная попытка откатывает всю транзакцию.
    """
    if delta == 0:
        return
    cur = conn.execute(
        "UPDATE users SET balance = balance + ? WHERE tg_id = ? AND balance + ? >= 0",
        (delta, user_id, delta),
    )
    if cur.rowcount == 0:
        row = conn.execute("SELECT balance FROM users WHERE tg_id = ?", (user_id,)).fetchone()
        if row is None:
            raise DomainError("Пользователь не найден", code="unknown_user", status=404)
        raise InsufficientCredits(-delta, row["balance"])
    try:
        conn.execute(
            "INSERT INTO credit_ledger (user_id, delta, reason, order_id, payment_id, note, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, delta, reason, order_id, payment_id, note, now()),
        )
    except sqlite3.IntegrityError as e:
        raise DuplicateOperation("Операция уже была выполнена") from e


def get_balance(db: Database, user_id: int) -> int:
    with db.read() as conn:
        row = conn.execute("SELECT balance FROM users WHERE tg_id = ?", (user_id,)).fetchone()
    return row["balance"] if row else 0


def get_ledger(db: Database, user_id: int, limit: int = 50) -> list[dict]:
    with db.read() as conn:
        rows = conn.execute(
            "SELECT l.id, l.delta, l.reason, l.order_id, l.payment_id, l.note, l.created_at, o.kind AS kind "
            "FROM credit_ledger l LEFT JOIN orders o ON o.id = l.order_id WHERE l.user_id = ? ORDER BY l.id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def summary(db: Database, user_id: int) -> dict:
    """Мои токены: баланс, куплено, потрачено, возвращено, бонусные."""
    with db.read() as conn:
        rows = conn.execute("SELECT reason, SUM(delta) AS s FROM credit_ledger WHERE user_id = ? GROUP BY reason", (user_id,)).fetchall()
        bal = conn.execute("SELECT balance FROM users WHERE tg_id = ?", (user_id,)).fetchone()
    by = {r["reason"]: r["s"] or 0 for r in rows}
    return {
        "balance": bal["balance"] if bal else 0,
        "bought": by.get("purchase", 0),
        "spent": -by.get("order_charge", 0),
        "refunded": by.get("order_refund", 0),
        "bonus": by.get("welcome_bonus", 0) + by.get("purchase_bonus", 0) + max(by.get("admin_adjust", 0), 0),
    }
