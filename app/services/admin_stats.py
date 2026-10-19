"""Данные для админ-панели. Владелец видит деньги и пользователей, разработчик — технику."""
from __future__ import annotations

from ..db import Database
from ..errors import DomainError


def owner_overview(db: Database, star_usd_rate: float) -> dict:
    with db.read() as conn:
        one = lambda sql, *a: conn.execute(sql, a).fetchone()
        users = one("SELECT COUNT(*) AS n FROM users")["n"]
        by_kind = {
            (r["kind"], r["status"]): r["n"]
            for r in conn.execute("SELECT kind, status, COUNT(*) AS n FROM orders GROUP BY kind, status")
        }
        free_done = one("SELECT COUNT(*) AS n FROM orders WHERE used_free = 1 AND status = 'done'")["n"]
        real = one(
            "SELECT COUNT(*) AS n, COALESCE(SUM(amount_stars), 0) AS stars FROM payments "
            "WHERE status = 'paid' AND provider = 'stars'"
        )
        test = one("SELECT COUNT(*) AS n FROM payments WHERE status = 'paid' AND provider = 'test'")["n"]
        cost = one("SELECT COALESCE(SUM(provider_cost_usd), 0) AS c FROM orders WHERE status = 'done'")["c"]
        circulation = one("SELECT COALESCE(SUM(balance), 0) AS b FROM users")["b"]
    revenue = real["stars"] * star_usd_rate
    return {
        "users": users,
        "generations": {
            kind: {s: by_kind.get((kind, s), 0) for s in ("done", "failed", "processing", "created")}
            for kind in ("photo", "video", "audio")
        },
        "free_generations_done": free_done,
        "purchases": real["n"],
        "stars_received": real["stars"],
        "test_purchases": test,
        "ai_cost_usd": round(cost, 4),
        "revenue_usd_estimate": round(revenue, 2),
        "profit_usd_estimate": round(revenue - cost, 2),
        "credits_in_circulation": circulation,
        "note": "Прибыль приблизительная: выручка = Stars × STAR_USD_RATE, комиссии Telegram/магазинов не учтены.",
    }


def owner_users(db: Database, search: str = "", limit: int = 200) -> list[dict]:
    sql = (
        "SELECT u.tg_id, u.username, u.first_name, u.balance, u.is_pro, u.created_at, "
        "(SELECT COUNT(*) FROM orders o WHERE o.user_id = u.tg_id AND o.kind = 'photo' AND o.status = 'done') AS photos, "
        "(SELECT COUNT(*) FROM orders o WHERE o.user_id = u.tg_id AND o.kind = 'video' AND o.status = 'done') AS videos, "
        "(SELECT COALESCE(SUM(amount_stars), 0) FROM payments p WHERE p.user_id = u.tg_id AND p.status = 'paid' AND p.provider = 'stars') AS stars_spent "
        "FROM users u"
    )
    args: list = []
    if search:
        sql += " WHERE CAST(u.tg_id AS TEXT) LIKE ? OR u.username LIKE ? OR u.first_name LIKE ?"
        args += [f"%{search}%"] * 3
    sql += " ORDER BY u.created_at DESC LIMIT ?"
    args.append(limit)
    with db.read() as conn:
        return [dict(r) for r in conn.execute(sql, args).fetchall()]


def dev_errors(db: Database, limit: int = 100) -> list[dict]:
    with db.read() as conn:
        rows = conn.execute("SELECT * FROM error_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def dev_orders(db: Database, status: str = "", limit: int = 100) -> list[dict]:
    if status and status not in ("created", "processing", "done", "failed"):
        raise DomainError("Неизвестный статус")
    sql = (
        "SELECT o.id, o.user_id, o.kind, o.status, o.used_free, o.price_credits, o.source, o.provider, "
        "o.provider_cost_usd, o.is_stub, o.error, o.created_at, o.finished_at, t.title, t.model "
        "FROM orders o JOIN templates t ON t.id = o.template_id"
    )
    args: list = []
    if status:
        sql += " WHERE o.status = ?"
        args.append(status)
    sql += " ORDER BY o.id DESC LIMIT ?"
    args.append(limit)
    with db.read() as conn:
        return [dict(r) for r in conn.execute(sql, args).fetchall()]


def dev_costs(db: Database) -> list[dict]:
    with db.read() as conn:
        rows = conn.execute(
            "SELECT t.model AS model, o.kind AS kind, COUNT(*) AS generations, "
            "COALESCE(AVG(o.provider_cost_usd), 0) AS avg_cost_usd, COALESCE(SUM(o.provider_cost_usd), 0) AS total_cost_usd "
            "FROM orders o JOIN templates t ON t.id = o.template_id WHERE o.status = 'done' GROUP BY t.model, o.kind"
        ).fetchall()
    return [dict(r) for r in rows]


def dev_status_counts(db: Database) -> dict:
    with db.read() as conn:
        return {r["status"]: r["n"] for r in conn.execute("SELECT status, COUNT(*) AS n FROM orders GROUP BY status")}
