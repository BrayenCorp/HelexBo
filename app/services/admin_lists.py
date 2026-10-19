"""Списки админки с серверной фильтрацией и пагинацией: генерации, платежи, ошибки, активность, рефералы, маркетинг."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from ..db import Database
from ..errors import DomainError
from . import sources
from .admin_users import display_name

STATUS_RU = {"created": "В очереди", "processing": "В обработке", "done": "Успешно", "failed": "Ошибка"}
PAY_STATUS_RU = {"pending": "Ожидает", "paid": "Оплачен", "failed": "Ошибка", "refunded": "Возврат", "cancelled": "Отменён"}


def _page(page: int, size: int) -> tuple[int, int]:
    size = max(1, min(size, 100))
    return size, (max(page, 1) - 1) * size


def generations_list(db: Database, *, kind="", status="", provider="", category="", start="", end="", q="", page=1, size=25) -> dict:
    where, args = ["1 = 1"], []
    if kind in ("photo", "video", "audio"):
        where.append("o.kind = ?"); args.append(kind)
    if status:
        if status not in STATUS_RU:
            raise DomainError("Неизвестный статус")
        where.append("o.status = ?"); args.append(status)
    if provider:
        where.append("COALESCE(o.model, t.model) = ?"); args.append(provider)
    if category:
        where.append("t.category = ?"); args.append(category)
    for col, val, op in (("substr(o.created_at,1,10)", start, ">="), ("substr(o.created_at,1,10)", end, "<=")):
        if val:
            try:
                date.fromisoformat(val)
            except ValueError:
                raise DomainError("Дата в формате ГГГГ-ММ-ДД")
            where.append(f"{col} {op} ?"); args.append(val)
    if q.strip():
        qq = q.strip().lstrip("@")
        where.append("(CAST(o.user_id AS TEXT) LIKE ? OR u.username LIKE ? OR o.prompt LIKE ? OR CAST(o.id AS TEXT) = ?)")
        args += [f"%{qq}%", f"%{qq}%", f"%{qq}%", qq]
    cond = " AND ".join(where)
    size, offset = _page(page, size)
    frm = "FROM orders o JOIN templates t ON t.id = o.template_id JOIN users u ON u.tg_id = o.user_id LEFT JOIN categories c ON c.id = t.category"
    with db.read() as c:
        total = c.execute(f"SELECT COUNT(*) {frm} WHERE {cond}", args).fetchone()[0]
        rows = [dict(r) for r in c.execute(
            f"SELECT o.id, o.user_id, u.username, u.first_name, o.kind, o.prompt, o.style, o.status, o.price_credits, o.used_free, o.provider_cost_usd, "
            f"o.created_at, o.error, o.is_stub, COALESCE(o.model, t.model) AS provider, t.title AS template, t.style_label, t.is_system, c.title AS category, "
            f"CASE WHEN o.started_at IS NOT NULL AND o.finished_at IS NOT NULL THEN (julianday(o.finished_at) - julianday(o.started_at)) * 86400 END AS seconds "
            f"{frm} WHERE {cond} ORDER BY o.id DESC LIMIT ? OFFSET ?", [*args, size, offset])]
    for r in rows:
        r["user"] = display_name({"username": r["username"], "first_name": r["first_name"], "tg_id": r["user_id"]})
        r["status_label"] = STATUS_RU.get(r["status"], r["status"])
        r["seconds"] = round(r["seconds"], 1) if r["seconds"] is not None else None
        if r["is_system"]:
            r["template"], r["category"] = "Свободная генерация", "—"
    return {"items": rows, "total": total, "page": page, "size": size}


def payments_list(db: Database, *, status="", method="", q="", page=1, size=25) -> dict:
    where, args = ["1 = 1"], []
    if status:
        if status not in PAY_STATUS_RU:
            raise DomainError("Неизвестный статус")
        where.append("p.status = ?"); args.append(status)
    if method:
        where.append("p.provider = ?"); args.append(method)
    if q.strip():
        qq = q.strip().lstrip("@")
        where.append("(CAST(p.user_id AS TEXT) LIKE ? OR u.username LIKE ? OR CAST(p.id AS TEXT) = ?)")
        args += [f"%{qq}%", f"%{qq}%", qq]
    cond = " AND ".join(where)
    size, offset = _page(page, size)
    frm = "FROM payments p JOIN users u ON u.tg_id = p.user_id JOIN packages k ON k.id = p.package_id"
    with db.read() as c:
        total = c.execute(f"SELECT COUNT(*) {frm} WHERE {cond}", args).fetchone()[0]
        rows = [dict(r) for r in c.execute(
            f"SELECT p.id, p.user_id, u.username, u.first_name, k.title AS product, p.amount, p.currency, p.amount_stars, p.credits, p.bonus, "
            f"p.provider AS method, p.status, p.created_at, p.paid_at {frm} WHERE {cond} ORDER BY p.id DESC LIMIT ? OFFSET ?", [*args, size, offset])]
    for r in rows:
        r["user"] = display_name({"username": r["username"], "first_name": r["first_name"], "tg_id": r["user_id"]})
        r["status_label"] = PAY_STATUS_RU.get(r["status"], r["status"])
    return {"items": rows, "total": total, "page": page, "size": size}


def errors_report(db: Database, *, severity="", provider="", page=1, size=25) -> dict:
    now = datetime.now(timezone.utc)
    where, args = ["1 = 1"], []
    if severity:
        where.append("e.severity = ?"); args.append(severity)
    if provider:
        where.append("e.provider = ?"); args.append(provider)
    cond = " AND ".join(where)
    size, offset = _page(page, size)
    cut = lambda d: (now - timedelta(days=d)).isoformat()
    with db.read() as c:
        one = lambda sql, *a: c.execute(sql, a).fetchone()[0]
        total = c.execute(f"SELECT COUNT(*) FROM error_log e WHERE {cond}", args).fetchone()[0]
        rows = [dict(r) for r in c.execute(
            f"SELECT e.id, e.created_at, e.source, e.order_id, e.message, e.user_id, e.provider, COALESCE(e.error_type, 'unknown') AS error_type, e.severity, u.username "
            f"FROM error_log e LEFT JOIN users u ON u.tg_id = e.user_id WHERE {cond} ORDER BY e.id DESC LIMIT ? OFFSET ?", [*args, size, offset])]
        today = now.date().isoformat()
        gens24 = one("SELECT COUNT(*) FROM orders WHERE created_at >= ?", cut(1))
        fails24 = one("SELECT COUNT(*) FROM orders WHERE status = 'failed' AND created_at >= ?", cut(1))
        gens7 = one("SELECT COUNT(*) FROM orders WHERE created_at >= ?", cut(7))
        fails7 = one("SELECT COUNT(*) FROM orders WHERE status = 'failed' AND created_at >= ?", cut(7))
        stats = {"today": one("SELECT COUNT(*) FROM error_log WHERE substr(created_at,1,10) = ?", today),
                 "h24": one("SELECT COUNT(*) FROM error_log WHERE created_at >= ?", cut(1)),
                 "d7": one("SELECT COUNT(*) FROM error_log WHERE created_at >= ?", cut(7)),
                 "rate_24h": round(fails24 * 100 / gens24, 1) if gens24 else None,
                 "rate_7d": round(fails7 * 100 / gens7, 1) if gens7 else None}
        providers = [r[0] for r in c.execute("SELECT DISTINCT provider FROM error_log WHERE provider IS NOT NULL ORDER BY 1")]
    for r in rows:
        r["user"] = f"@{r['username']}" if r["username"] else (f"ID {r['user_id']}" if r["user_id"] else "—")
    return {"items": rows, "total": total, "page": page, "size": size, "stats": stats, "providers": providers}


def activity_feed(db: Database, *, limit: int = 50, kinds: set[str] | None = None) -> list[dict]:
    """Последняя активность: собирается из реальных таблиц (регистрации, заказы, платежи, события, действия админов)."""
    n = max(1, min(limit, 200))
    items: list[dict] = []
    with db.read() as c:
        def who(r) -> str:
            return display_name({"username": r["username"], "first_name": r["first_name"], "tg_id": r["user_id"]})
        for r in c.execute("SELECT tg_id AS user_id, username, first_name, registered_at AS ts FROM users WHERE registered_at IS NOT NULL ORDER BY registered_at DESC LIMIT ?", (n,)):
            items.append({"ts": r["ts"], "type": "registration", "user_id": r["user_id"], "user": who(r), "text": "зарегистрировался(-ась)", "amount": None})
        for r in c.execute("SELECT o.user_id, u.username, u.first_name, o.kind, o.status, o.created_at, o.finished_at, o.price_credits FROM orders o "
                           "JOIN users u ON u.tg_id = o.user_id ORDER BY o.id DESC LIMIT ?", (n,)):
            what = {"photo": "изображение", "video": "видео", "audio": "аудио"}.get(r["kind"], "работу")
            if r["status"] == "done":
                typ, text, ts = ("video" if r["kind"] == "video" else "photo"), f"создал(-а) {what}", r["finished_at"] or r["created_at"]
            elif r["status"] == "failed":
                typ, text, ts = "error", "получил(-а) ошибку генерации", r["finished_at"] or r["created_at"]
            else:
                typ, text, ts = "started", f"запустил(-а) генерацию ({what})", r["created_at"]
            items.append({"ts": ts, "type": typ, "user_id": r["user_id"], "user": who(r), "text": text, "amount": -r["price_credits"] if r["price_credits"] else None})
        for r in c.execute("SELECT p.user_id, u.username, u.first_name, p.credits, p.bonus, p.paid_at AS ts FROM payments p JOIN users u ON u.tg_id = p.user_id "
                           "WHERE p.status = 'paid' AND p.provider = 'stars' ORDER BY p.paid_at DESC LIMIT ?", (n,)):
            items.append({"ts": r["ts"], "type": "purchase", "user_id": r["user_id"], "user": who(r), "text": f"купил(-а) {r['credits'] + r['bonus']} токенов", "amount": r["credits"] + r["bonus"]})
        for r in c.execute("SELECT e.user_id, u.username, u.first_name, e.name, e.ts FROM events e JOIN users u ON u.tg_id = e.user_id "
                           "WHERE e.name IN ('pro_enabled', 'pro_cancelled') ORDER BY e.id DESC LIMIT ?", (n,)):
            items.append({"ts": r["ts"], "type": "pro", "user_id": r["user_id"], "user": who(r),
                          "text": "получил(-а) тариф PRO" if r["name"] == "pro_enabled" else "тариф PRO отключён", "amount": None})
        for r in c.execute("SELECT admin_name, action, target_user_id, ts FROM admin_audit ORDER BY id DESC LIMIT ?", (n,)):
            items.append({"ts": r["ts"], "type": "admin", "user_id": r["target_user_id"], "user": r["admin_name"], "text": f"администратор: {r['action'].lower()}", "amount": None})
    if kinds:
        items = [i for i in items if i["type"] in kinds]
    items.sort(key=lambda i: i["ts"] or "", reverse=True)
    return items[:n]


def referrals(db: Database, bot_username: str = "") -> dict:
    cut = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    paid = "EXISTS (SELECT 1 FROM payments p WHERE p.user_id = u.tg_id AND p.status = 'paid' AND p.provider = 'stars')"
    rev = "(SELECT COALESCE(SUM(p.amount_stars),0) FROM payments p WHERE p.user_id = u.tg_id AND p.status = 'paid' AND p.provider = 'stars')"
    with db.read() as c:
        rows = [dict(r) for r in c.execute(
            f"SELECT r.tg_id, r.username, r.first_name, COUNT(u.tg_id) AS invited, SUM(u.last_seen_at >= ?) AS active, SUM({paid}) AS paying, SUM({rev}) AS revenue "
            f"FROM users u JOIN users r ON r.tg_id = u.referrer_id GROUP BY r.tg_id ORDER BY invited DESC LIMIT 100", (cut,))]
        tot = c.execute(f"SELECT COUNT(*) AS invited, SUM(u.last_seen_at >= ?) AS active, SUM({paid}) AS paying, SUM({rev}) AS revenue FROM users u WHERE u.referrer_id IS NOT NULL", (cut,)).fetchone()
    for r in rows:
        r["name"] = display_name({"username": r["username"], "first_name": r["first_name"], "tg_id": r["tg_id"]})
        r["link"] = f"https://t.me/{bot_username}?start=ref_{r['tg_id']}" if bot_username else f"?start=ref_{r['tg_id']}"
        r["active"], r["paying"], r["revenue"] = r["active"] or 0, r["paying"] or 0, r["revenue"] or 0
        r["conversion"] = round(r["paying"] * 100 / r["invited"], 1) if r["invited"] else None
    invited = tot["invited"] or 0
    return {"items": rows, "totals": {"invited": invited, "active": tot["active"] or 0, "paying": tot["paying"] or 0, "revenue": tot["revenue"] or 0,
                                     "conversion": round((tot["paying"] or 0) * 100 / invited, 1) if invited else None},
            "link_format": f"https://t.me/{bot_username or '<бот>'}?start=ref_<Telegram ID пригласившего>"}


def marketing(db: Database, bot_username: str = "") -> dict:
    paid = "EXISTS (SELECT 1 FROM payments p WHERE p.user_id = u.tg_id AND p.status = 'paid' AND p.provider = 'stars')"
    rev = "(SELECT COALESCE(SUM(p.amount_stars),0) FROM payments p WHERE p.user_id = u.tg_id AND p.status = 'paid' AND p.provider = 'stars')"
    gen = "EXISTS (SELECT 1 FROM orders o WHERE o.user_id = u.tg_id AND o.status = 'done')"
    with db.read() as c:
        rows = [dict(r) for r in c.execute(
            f"SELECT u.source, u.campaign, u.material, COUNT(*) AS users, SUM(u.registered_at IS NOT NULL) AS registered, SUM({gen}) AS generated, "
            f"SUM({paid}) AS paying, SUM({rev}) AS revenue FROM users u GROUP BY u.source, u.campaign, u.material ORDER BY users DESC LIMIT 200")]
    for r in rows:
        r["source_label"] = sources.label(r["source"])
        r["conversion"] = round((r["paying"] or 0) * 100 / r["users"], 1) if r["users"] else None
        for k in ("registered", "generated", "paying", "revenue"):
            r[k] = r[k] or 0
    return {"items": rows, "link_format": f"https://t.me/{bot_username or '<бот>'}?start=src_<источник>_<кампания>_<материал>",
            "note": "Источник сохраняется только если он реально пришёл в ссылке запуска (?start=…). Если параметра не было — «Не определён»."}
