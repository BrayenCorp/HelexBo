"""Пользователи в админке: список с фильтрами и пагинацией, профиль с таймлайном, действия с журналом."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from ..db import Database, now
from ..errors import DomainError
from . import credits, events, sources

FILTERS = ("all", "new", "active", "inactive", "pro", "free", "paying", "nonpaying", "top_active", "top_spenders", "blocked")
SPENT = "(SELECT COALESCE(SUM(p.amount_stars),0) FROM payments p WHERE p.user_id = u.tg_id AND p.status = 'paid' AND p.provider = 'stars')"
GENS = "(SELECT COUNT(*) FROM orders o WHERE o.user_id = u.tg_id AND o.status = 'done'%s)"
G_ALL = GENS % ""
G_PHOTO = GENS % " AND o.kind = 'photo'"
G_VIDEO = GENS % " AND o.kind = 'video'"


def display_name(u: dict) -> str:
    return f"@{u['username']}" if u.get("username") else (u.get("first_name") or f"ID {u['tg_id']}")


def _like_variants(q: str) -> list[str]:
    return list({q, q.lower(), q.upper(), q.capitalize(), q.title()})  # LIKE в SQLite не различает регистр только для латиницы


def users_list(db: Database, *, q: str = "", flt: str = "all", page: int = 1, size: int = 25) -> dict:
    if flt not in FILTERS:
        raise DomainError("Неизвестный фильтр")
    size = max(1, min(size, 100))
    t = datetime.now(timezone.utc)
    where, args = ["1 = 1"], []
    if q.strip():
        like = []
        for v in _like_variants(q.strip().lstrip("@")):
            like.append("(CAST(u.tg_id AS TEXT) LIKE ? OR u.username LIKE ? OR u.first_name LIKE ? OR u.last_name LIKE ?)")
            args += [f"%{v}%"] * 4
        where.append("(" + " OR ".join(like) + ")")
    order = "u.created_at DESC"
    if flt == "new":
        where.append("u.created_at >= ?"); args.append((t - timedelta(days=7)).isoformat())
    elif flt == "active":
        where.append("u.last_seen_at >= ?"); args.append((t - timedelta(days=7)).isoformat())
    elif flt == "inactive":
        where.append("(u.last_seen_at IS NULL OR u.last_seen_at < ?)"); args.append((t - timedelta(days=30)).isoformat())
    elif flt == "pro":
        where.append("u.is_pro = 1")
    elif flt == "free":
        where.append("u.is_pro = 0")
    elif flt == "paying":
        where.append(f"{SPENT} > 0")
    elif flt == "nonpaying":
        where.append(f"{SPENT} = 0")
    elif flt == "top_active":
        order = "generations DESC, u.created_at DESC"
    elif flt == "top_spenders":
        where.append(f"{SPENT} > 0"); order = "spent_stars DESC"
    elif flt == "blocked":
        where.append("u.status = 'blocked'")
    cond = " AND ".join(where)
    sql = (
        "SELECT u.tg_id, u.username, u.first_name, u.last_name, u.created_at, u.last_seen_at, u.is_pro, u.balance, u.source, u.campaign, u.status, "
        f"{SPENT} AS spent_stars, "
        "(SELECT COALESCE(-SUM(l.delta),0) FROM credit_ledger l WHERE l.user_id = u.tg_id AND l.reason = 'order_charge') AS spent_credits, "
        f"{G_ALL} AS generations, {G_PHOTO} AS photos, {G_VIDEO} AS videos "
        f"FROM users u WHERE {cond} ORDER BY {order} LIMIT ? OFFSET ?"
    )
    with db.read() as c:
        total = c.execute(f"SELECT COUNT(*) FROM users u WHERE {cond}", args).fetchone()[0]
        rows = [dict(r) for r in c.execute(sql, [*args, size, (max(page, 1) - 1) * size]).fetchall()]
    for r in rows:
        r["tariff"] = "PRO" if r["is_pro"] else "Бесплатный"
        r["source_label"] = sources.label(r["source"])
        r["name"] = display_name(r)
    return {"items": rows, "total": total, "page": page, "size": size}


def user_profile(db: Database, tg_id: int, star_rate: float) -> dict:
    with db.read() as c:
        u = c.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,)).fetchone()
        if u is None:
            raise DomainError("Пользователь не найден", code="not_found", status=404)
        u = dict(u)
        one = lambda sql, *a: c.execute(sql, a).fetchone()
        pay = one("SELECT COUNT(*) AS n, COALESCE(SUM(amount_stars),0) AS stars, MIN(paid_at) AS first, MAX(paid_at) AS last FROM payments "
                  "WHERE user_id = ? AND status = 'paid' AND provider = 'stars'", tg_id)
        led = {r["reason"]: r["s"] or 0 for r in c.execute("SELECT reason, SUM(delta) AS s FROM credit_ledger WHERE user_id = ? GROUP BY reason", (tg_id,))}
        gen = {(r["kind"], r["status"]): r["n"] for r in c.execute("SELECT kind, status, COUNT(*) AS n FROM orders WHERE user_id = ? GROUP BY kind, status", (tg_id,))}
        g = lambda kind=None, status=None: sum(n for (k, s), n in gen.items() if (kind is None or k == kind) and (status is None or s == status))
        orders = [dict(r) for r in c.execute(
            "SELECT o.id, o.created_at, o.kind, o.status, o.prompt, o.style, o.price_credits, o.used_free, o.provider_cost_usd, o.error, "
            "COALESCE(o.model, t.model) AS model, t.title AS template, t.is_system, "
            "CASE WHEN o.started_at IS NOT NULL AND o.finished_at IS NOT NULL THEN (julianday(o.finished_at) - julianday(o.started_at)) * 86400 END AS seconds "
            "FROM orders o JOIN templates t ON t.id = o.template_id WHERE o.user_id = ? ORDER BY o.id DESC LIMIT 50", (tg_id,))]
        payments = [dict(r) for r in c.execute(
            "SELECT p.id, p.amount, p.currency, p.amount_stars, p.credits, p.bonus, p.provider, p.status, p.created_at, p.paid_at, k.title AS product "
            "FROM payments p JOIN packages k ON k.id = p.package_id WHERE p.user_id = ? ORDER BY p.id DESC LIMIT 50", (tg_id,))]
        evs = [dict(r) for r in c.execute("SELECT ts, name, props FROM events WHERE user_id = ? ORDER BY id DESC LIMIT 100", (tg_id,))]
        ledger_ev = [dict(r) for r in c.execute(
            "SELECT created_at AS ts, reason, delta, note FROM credit_ledger WHERE user_id = ? AND reason IN ('welcome_bonus','order_refund','purchase_bonus') ORDER BY id DESC LIMIT 50", (tg_id,))]
        audit = [dict(r) for r in c.execute("SELECT ts, admin_name, action, note FROM admin_audit WHERE target_user_id = ? ORDER BY id DESC LIMIT 30", (tg_id,))]
        referred = one("SELECT COUNT(*) AS n FROM users WHERE referrer_id = ?", tg_id)["n"]
        ref_by = one("SELECT username, first_name, tg_id FROM users WHERE tg_id = ?", u["referrer_id"]) if u["referrer_id"] else None

    tl = []
    if u["registered_at"]:
        tl.append((u["registered_at"], "Регистрация в Nolla AI"))
    labels = {"bot_started": "Запуск бота", "miniapp_opened": "Открыл Mini App", "pro_enabled": "Подключён PRO", "pro_cancelled": "PRO отключён"}
    seen_once = set()
    for e in reversed(evs):
        if e["name"] in ("bot_started", "miniapp_opened") and e["name"] in seen_once:
            continue
        seen_once.add(e["name"])
        if e["name"] in labels:
            tl.append((e["ts"], labels[e["name"]]))
    done = [o for o in reversed(orders) if o["status"] == "done"]
    if done:
        tl.append((done[0]["created_at"], "Первая генерация"))
    for o in orders:
        what = "изображение" if o["kind"] == "photo" else "видео"
        tl.append((o["created_at"], {"done": f"Создано {what}", "failed": f"Ошибка генерации ({what})"}.get(o["status"], f"Запущена генерация ({what})")))
    for p in payments:
        if p["status"] == "paid" and p["provider"] != "test":
            tl.append((p["paid_at"] or p["created_at"], f"Покупка токенов: {p['credits'] + p['bonus']}"))
    for r in ledger_ev:
        text = {"welcome_bonus": f"Стартовый бонус: +{r['delta']}", "order_refund": f"Возврат токенов: +{r['delta']}",
                "purchase_bonus": f"Бонус к пакету: +{r['delta']}"}[r["reason"]]
        tl.append((r["ts"], text))
    for a in audit:
        tl.append((a["ts"], f"{a['action']} ({a['admin_name']})"))
    tl.sort(key=lambda x: x[0] or "")

    spent = pay["stars"]
    return {
        "info": {"tg_id": u["tg_id"], "username": u["username"], "first_name": u["first_name"], "last_name": u["last_name"], "name": display_name(u),
                 "created_at": u["created_at"], "registered_at": u["registered_at"], "last_seen_at": u["last_seen_at"],
                 "tariff": "PRO" if u["is_pro"] else "Бесплатный", "is_pro": bool(u["is_pro"]), "status": u["status"],
                 "source": sources.label(u["source"]), "campaign": u["campaign"], "material": u["material"],
                 "language": u["language_code"], "photo_url": u["photo_url"], "invited": referred,
                 "referrer": ({"tg_id": ref_by["tg_id"], "name": display_name(dict(ref_by))} if ref_by else None)},
        "money": {"spent_stars": spent, "spent_usd_estimate": round(spent * star_rate, 2), "purchases": pay["n"],
                  "avg_check": round(spent / pay["n"], 1) if pay["n"] else 0, "first": pay["first"], "last": pay["last"],
                  "ltv_stars": spent, "ltv_usd_estimate": round(spent * star_rate, 2)},
        "tokens": {"balance": u["balance"], "bought": led.get("purchase", 0), "spent": -led.get("order_charge", 0), "refunded": led.get("order_refund", 0),
                   "bonus": led.get("welcome_bonus", 0) + led.get("purchase_bonus", 0) + max(led.get("admin_adjust", 0), 0)},
        "generations": {"total": g(), "photo": g("photo"), "video": g("video"), "success": g(status="done"), "errors": g(status="failed")},
        "timeline": [{"ts": ts, "text": text} for ts, text in tl][-200:],
        "orders": orders, "payments": payments,
    }


ACTIONS = {
    "credits_add": "Начисление токенов", "credits_sub": "Списание токенов", "pro_on": "Назначение тарифа PRO", "pro_off": "Снятие тарифа PRO",
    "block": "Блокировка пользователя", "unblock": "Разблокировка пользователя", "reset_free": "Сброс бесплатных попыток",
}


def act(db: Database, admin: dict, tg_id: int, action: str, *, amount: int | None = None, note: str = "", confirm: bool = False) -> dict:
    """Действие администратора. Требует подтверждения, пишет «было → стало» в журнал и в события."""
    if action not in ACTIONS:
        raise DomainError("Неизвестное действие")
    if not confirm:
        raise DomainError("Действие нужно подтвердить", code="confirm_required")
    if action in ("credits_add", "credits_sub"):
        if not isinstance(amount, int) or amount <= 0 or amount > 1_000_000:
            raise DomainError("Укажите количество токенов (целое число больше нуля)")
    with db.tx() as conn:
        u = conn.execute("SELECT balance, is_pro, status FROM users WHERE tg_id = ?", (tg_id,)).fetchone()
        if u is None:
            raise DomainError("Пользователь не найден", code="not_found", status=404)
        free_before = conn.execute("SELECT COUNT(*) FROM orders WHERE user_id = ? AND used_free = 1", (tg_id,)).fetchone()[0]
        before = {"баланс": u["balance"], "тариф": "PRO" if u["is_pro"] else "Бесплатный", "статус": u["status"], "бесплатные попытки использовано": free_before}
        if action == "credits_add":
            credits.apply(conn, tg_id, amount, "admin_adjust", note=note or "Начисление администратором")
        elif action == "credits_sub":
            credits.apply(conn, tg_id, -amount, "admin_adjust", note=note or "Списание администратором")
        elif action in ("pro_on", "pro_off"):
            conn.execute("UPDATE users SET is_pro = ? WHERE tg_id = ?", (1 if action == "pro_on" else 0, tg_id))
            events.log_conn(conn, "pro_enabled" if action == "pro_on" else "pro_cancelled", tg_id, by=admin["id"])
        elif action in ("block", "unblock"):
            conn.execute("UPDATE users SET status = ? WHERE tg_id = ?", ("blocked" if action == "block" else "active", tg_id))
        elif action == "reset_free":
            conn.execute("UPDATE orders SET used_free = 2 WHERE user_id = ? AND used_free = 1", (tg_id,))
        u2 = conn.execute("SELECT balance, is_pro, status FROM users WHERE tg_id = ?", (tg_id,)).fetchone()
        free_after = conn.execute("SELECT COUNT(*) FROM orders WHERE user_id = ? AND used_free = 1", (tg_id,)).fetchone()[0]
        after = {"баланс": u2["balance"], "тариф": "PRO" if u2["is_pro"] else "Бесплатный", "статус": u2["status"], "бесплатные попытки использовано": free_after}
        label = ACTIONS[action] + (f": {amount}" if amount else "")
        conn.execute(
            "INSERT INTO admin_audit (ts, admin_id, admin_name, action, target_user_id, before, after, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (now(), admin["id"], display_name({"username": admin.get("username"), "first_name": admin.get("first_name"), "tg_id": admin["id"]}),
             label, tg_id, json.dumps(before, ensure_ascii=False), json.dumps(after, ensure_ascii=False), note[:300]),
        )
        events.log_conn(conn, "admin_action", tg_id, action=action, by=admin["id"])
    return {"before": before, "after": after}


def audit_list(db: Database, page: int = 1, size: int = 30) -> dict:
    size = max(1, min(size, 100))
    with db.read() as c:
        total = c.execute("SELECT COUNT(*) FROM admin_audit").fetchone()[0]
        rows = [dict(r) for r in c.execute(
            "SELECT a.*, u.username AS target_username, u.first_name AS target_first_name FROM admin_audit a "
            "LEFT JOIN users u ON u.tg_id = a.target_user_id ORDER BY a.id DESC LIMIT ? OFFSET ?", (size, (max(page, 1) - 1) * size))]
    for r in rows:
        r["before"] = json.loads(r["before"] or "{}")
        r["after"] = json.loads(r["after"] or "{}")
        r["target"] = f"@{r['target_username']}" if r["target_username"] else (r["target_first_name"] or (f"ID {r['target_user_id']}" if r["target_user_id"] else ""))
    return {"items": rows, "total": total, "page": page, "size": size}
