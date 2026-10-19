"""Пакеты кредитов и платежи.

Кредиты начисляются ТОЛЬКО в confirm_payment — после подтверждения оплаты:
* test — кнопка «тестовая оплата» (реальных денег нет);
* stars — Telegram Stars: подтверждение приходит от Telegram (successful_payment в боте).
Повторное подтверждение того же платежа или того же telegram_payment_charge_id кредиты не добавляет.
"""
from __future__ import annotations

import secrets
import sqlite3
import uuid

from ..db import Database, now
from ..errors import DomainError, DuplicateOperation
from . import credits


def list_packages(db: Database) -> list[dict]:
    with db.read() as conn:
        rows = conn.execute("SELECT * FROM packages WHERE is_active = 1 ORDER BY sort_order, id").fetchall()
    return [dict(r) for r in rows]


def create_payment(db: Database, user_id: int, package_id: str, provider: str) -> dict:
    """provider: stars | test | любой другой код способа оплаты (сумма берётся из price_rub и считается в RUB)."""
    if not provider or len(provider) > 20:
        raise DomainError("Неизвестный способ оплаты")
    with db.tx() as conn:
        pkg = conn.execute("SELECT * FROM packages WHERE id = ? AND is_active = 1", (package_id,)).fetchone()
        if pkg is None:
            raise DomainError("Пакет не найден", code="package_not_found", status=404)
        if provider in ("stars", "test"):
            stars, amount, currency = pkg["price_stars"], float(pkg["price_stars"]), "XTR" if provider == "stars" else "TEST"
        else:
            if not pkg["price_rub"]:
                raise DomainError("Для этого пакета не задана цена в рублях", code="no_price")
            stars, amount, currency = 0, float(pkg["price_rub"]), "RUB"
        cur = conn.execute(
            "INSERT INTO payments (user_id, package_id, credits, bonus, amount_stars, amount, currency, provider, status, payload, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)",
            (user_id, pkg["id"], pkg["credits"], pkg["bonus"], stars, amount, currency, provider, secrets.token_urlsafe(16), now()),
        )
        row = conn.execute("SELECT * FROM payments WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


def get_by_payload(db: Database, payload: str) -> dict | None:
    with db.read() as conn:
        row = conn.execute("SELECT * FROM payments WHERE payload = ?", (payload,)).fetchone()
    return dict(row) if row else None


def confirm_payment(
    db: Database,
    payload: str,
    *,
    provider: str,
    provider_charge_id: str | None = None,
    paid_stars: int | None = None,
    user_id: int | None = None,
) -> tuple[dict, bool]:
    """Подтвердить платёж. Возвращает (платёж, начислены_ли_кредиты_сейчас)."""
    try:
        with db.tx() as conn:
            row = conn.execute("SELECT * FROM payments WHERE payload = ?", (payload,)).fetchone()
            if row is None:
                raise DomainError("Платёж не найден", code="payment_not_found", status=404)
            pay = dict(row)
            if user_id is not None and pay["user_id"] != user_id:
                raise DomainError("Платёж принадлежит другому пользователю", code="forbidden", status=403)
            if pay["provider"] != provider:
                raise DomainError("Способ оплаты не совпадает", code="provider_mismatch")
            if pay["status"] == "paid":
                return pay, False
            if paid_stars is not None and provider == "stars" and paid_stars != pay["amount_stars"]:
                raise DomainError("Сумма платежа не совпадает с ценой пакета", code="amount_mismatch")
            conn.execute(
                "UPDATE payments SET status = 'paid', paid_at = ?, provider_charge_id = ? "
                "WHERE id = ? AND status = 'pending'",
                (now(), provider_charge_id, pay["id"]),
            )
            credits.apply(conn, pay["user_id"], pay["credits"], "purchase", payment_id=pay["id"])
            if pay["bonus"] > 0:
                credits.apply(conn, pay["user_id"], pay["bonus"], "purchase_bonus", payment_id=pay["id"], note="Бонус к пакету")
            row = conn.execute("SELECT * FROM payments WHERE id = ?", (pay["id"],)).fetchone()
            return dict(row), True
    except sqlite3.IntegrityError as e:  # тот же provider_charge_id уже использован
        raise DuplicateOperation("Этот платёж уже обработан") from e


def list_user_payments(db: Database, user_id: int, limit: int = 50) -> list[dict]:
    with db.read() as conn:
        rows = conn.execute(
            "SELECT p.id, p.credits, p.bonus, p.amount_stars, p.amount, p.currency, p.provider, p.status, p.created_at, p.paid_at, k.title AS package "
            "FROM payments p JOIN packages k ON k.id = p.package_id WHERE p.user_id = ? AND p.status = 'paid' "
            "ORDER BY p.id DESC LIMIT ?", (user_id, limit)
        ).fetchall()
    return [dict(r) for r in rows]


# ---- управление пакетами (админ-панель) ----

def admin_list_packages(db: Database) -> list[dict]:
    with db.read() as conn:
        rows = conn.execute(
            "SELECT k.*, (SELECT COUNT(*) FROM payments p WHERE p.package_id = k.id AND p.status = 'paid') AS sales "
            "FROM packages k ORDER BY k.sort_order, k.id"
        ).fetchall()
    return [dict(r) for r in rows]


def _clean_package(fields: dict, partial: bool) -> dict:
    out: dict = {}
    if "title" in fields:
        out["title"] = str(fields["title"]).strip()[:60]
        if not out["title"]:
            raise DomainError("Название не может быть пустым")
    elif not partial:
        raise DomainError("Укажите название пакета")
    for key, label in (("credits", "Количество кредитов"), ("price_stars", "Цена в Stars")):
        if key in fields:
            try:
                out[key] = int(fields[key])
            except (TypeError, ValueError):
                raise DomainError(f"{label} должно быть числом")
            if out[key] <= 0:
                raise DomainError(f"{label} должно быть больше нуля")
        elif not partial:
            raise DomainError(f"Укажите: {label.lower()}")
    if "sort_order" in fields:
        try:
            out["sort_order"] = int(fields["sort_order"])
        except (TypeError, ValueError):
            raise DomainError("Порядок должен быть числом")
    if "badge" in fields:
        out["badge"] = str(fields["badge"]).strip()[:30]
    for key in ("bonus", "old_price_stars", "price_rub"):
        if key in fields:
            raw = fields[key]
            if raw in (None, "") and key != "bonus":
                out[key] = None
                continue
            try:
                out[key] = int(raw or 0)
            except (TypeError, ValueError):
                raise DomainError(f"Поле «{key}» должно быть числом")
            if out[key] < 0:
                raise DomainError("Значение не может быть отрицательным")
    if "is_active" in fields:
        out["is_active"] = 1 if fields["is_active"] in (True, 1, "1", "true", "True") else 0
    return out


def create_package(db: Database, fields: dict) -> dict:
    data = _clean_package(fields, partial=False)
    pid = f"pk-{uuid.uuid4().hex[:6]}"
    cols = ["id", *data.keys()]
    with db.tx() as conn:
        conn.execute(f"INSERT INTO packages ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})", [pid, *data.values()])
        return dict(conn.execute("SELECT * FROM packages WHERE id = ?", (pid,)).fetchone())


def update_package(db: Database, package_id: str, fields: dict) -> dict:
    data = _clean_package(fields, partial=True)
    with db.tx() as conn:
        if conn.execute("SELECT 1 FROM packages WHERE id = ?", (package_id,)).fetchone() is None:
            raise DomainError("Пакет не найден", code="package_not_found", status=404)
        if data:
            conn.execute(f"UPDATE packages SET {', '.join(f'{k} = ?' for k in data)} WHERE id = ?", [*data.values(), package_id])
        return dict(conn.execute("SELECT * FROM packages WHERE id = ?", (package_id,)).fetchone())


def delete_package(db: Database, package_id: str) -> dict:
    """Пакет с покупками не удаляется (история платежей), а отключается."""
    with db.tx() as conn:
        if conn.execute("SELECT 1 FROM packages WHERE id = ?", (package_id,)).fetchone() is None:
            raise DomainError("Пакет не найден", code="package_not_found", status=404)
        used = conn.execute("SELECT COUNT(*) AS n FROM payments WHERE package_id = ?", (package_id,)).fetchone()["n"]
        if used:
            conn.execute("UPDATE packages SET is_active = 0 WHERE id = ?", (package_id,))
            return {"deleted": False, "hidden": True}
        conn.execute("DELETE FROM packages WHERE id = ?", (package_id,))
        return {"deleted": True, "hidden": False}
