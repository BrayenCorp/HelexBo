"""Аналитика Nolla AI. ВСЕ цифры считаются из реальной базы (SQL-агрегации на сервере); если данных нет — 0 или None.
Периоды: today | yesterday | 7d | 30d | 90d | year | custom (start, end в формате ГГГГ-ММ-ДД, UTC)."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from ..db import Database
from ..errors import DomainError

REAL = "p.status = 'paid' AND p.provider = 'stars'"  # реальные платежи; тестовые в выручку не входят


def today() -> date:
    return datetime.now(timezone.utc).date()


def resolve_period(period: str = "30d", start: str | None = None, end: str | None = None) -> tuple[date, date]:
    t = today()
    if period == "today":
        return t, t
    if period == "yesterday":
        return t - timedelta(days=1), t - timedelta(days=1)
    if period in ("7d", "30d", "90d"):
        return t - timedelta(days=int(period[:-1]) - 1), t
    if period == "year":
        return date(t.year, 1, 1), t
    if period == "custom":
        try:
            s, e = date.fromisoformat(start or ""), date.fromisoformat(end or "")
        except ValueError:
            raise DomainError("Укажите период в формате ГГГГ-ММ-ДД")
        if s > e or (e - s).days > 800:
            raise DomainError("Некорректный период")
        return s, e
    raise DomainError("Неизвестный период")


def days_between(s: date, e: date) -> list[str]:
    return [(s + timedelta(days=i)).isoformat() for i in range((e - s).days + 1)]


def _n(v) -> int:
    return int(v or 0)


def _pct(a, b):
    return round(a * 100 / b, 1) if b else None


def overview(db: Database, s: date, e: date, star_rate: float) -> dict:
    S, E = s.isoformat(), e.isoformat()
    t = today()
    with db.read() as c:
        one = lambda sql, *a: c.execute(sql, a).fetchone()[0]
        users_total = one("SELECT COUNT(*) FROM users")
        gens = {(r["kind"], r["status"]): r["n"] for r in c.execute(
            "SELECT kind, status, COUNT(*) AS n FROM orders WHERE substr(created_at,1,10) BETWEEN ? AND ? GROUP BY kind, status", (S, E))}
        g = lambda kind=None, status=None: sum(n for (k, st), n in gens.items() if (kind is None or k == kind) and (status is None or st == status))

        def revenue(a: date, b: date) -> int:
            return _n(one(f"SELECT SUM(p.amount_stars) FROM payments p WHERE {REAL} AND substr(p.paid_at,1,10) BETWEEN ? AND ?", a.isoformat(), b.isoformat()))

        purchases = one(f"SELECT COUNT(*) FROM payments p WHERE {REAL} AND substr(p.paid_at,1,10) BETWEEN ? AND ?", S, E)
        rev = revenue(s, e)
        others = [dict(r) for r in c.execute(
            "SELECT currency, SUM(amount) AS amount, COUNT(*) AS n FROM payments WHERE status = 'paid' AND provider NOT IN ('stars', 'test') "
            "AND substr(paid_at,1,10) BETWEEN ? AND ? GROUP BY currency", (S, E))]
        led = lambda reason: _n(one("SELECT SUM(delta) FROM credit_ledger WHERE reason = ? AND substr(created_at,1,10) BETWEEN ? AND ?", reason, S, E))
        sold = _n(one("SELECT SUM(l.delta) FROM credit_ledger l JOIN payments p ON p.id = l.payment_id WHERE l.reason = 'purchase' AND p.provider != 'test' "
                      "AND substr(l.created_at,1,10) BETWEEN ? AND ?", S, E))
        return {
            "period": {"start": S, "end": E},
            "users": {
                "total": users_total,
                "new": one("SELECT COUNT(*) FROM users WHERE substr(created_at,1,10) BETWEEN ? AND ?", S, E),
                "active": one("SELECT COUNT(DISTINCT user_id) FROM daily_activity WHERE day BETWEEN ? AND ?", S, E),
                "returned": one("SELECT COUNT(DISTINCT a.user_id) FROM daily_activity a JOIN users u ON u.tg_id = a.user_id "
                                "WHERE a.day BETWEEN ? AND ? AND substr(u.created_at,1,10) < ?", S, E, S),
            },
            "generations": {"total": g(), "photo": g("photo"), "video": g("video"), "audio": g("audio"), "success": g(status="done"), "errors": g(status="failed"),
                            "processing": g(status="processing") + g(status="created")},
            "money": {
                "revenue_stars": rev, "revenue_usd_estimate": round(rev * star_rate, 2), "purchases": purchases,
                "today": revenue(t, t), "d7": revenue(t - timedelta(days=6), t), "d30": revenue(t - timedelta(days=29), t),
                "avg_check": round(rev / purchases, 1) if purchases else 0, "other_currencies": others,
            },
            "tokens": {"sold": sold, "spent": -led("order_charge"), "refunded": led("order_refund"),
                       "bonus": led("welcome_bonus") + led("purchase_bonus"), "balance_total": _n(one("SELECT SUM(balance) FROM users"))},
            "subscriptions": {"free": one("SELECT COUNT(*) FROM users WHERE is_pro = 0"), "pro": one("SELECT COUNT(*) FROM users WHERE is_pro = 1"),
                              "granted": one("SELECT COUNT(*) FROM events WHERE name = 'pro_enabled' AND substr(ts,1,10) BETWEEN ? AND ?", S, E),
                              "cancelled": one("SELECT COUNT(*) FROM events WHERE name = 'pro_cancelled' AND substr(ts,1,10) BETWEEN ? AND ?", S, E)},
        }


def series(db: Database, s: date, e: date) -> dict:
    S, E = s.isoformat(), e.isoformat()
    days = days_between(s, e)
    out = {k: dict.fromkeys(days, 0) for k in (
        "users_new", "users_active", "users_returned", "revenue", "purchases", "photo", "video", "audio", "tokens_bought", "tokens_spent", "tokens_refunded")}
    with db.read() as c:
        def fill(key, sql, *a):
            for d, n in c.execute(sql, a).fetchall():
                if d in out[key]:
                    out[key][d] += n or 0
        fill("users_new", "SELECT substr(created_at,1,10), COUNT(*) FROM users WHERE substr(created_at,1,10) BETWEEN ? AND ? GROUP BY 1", S, E)
        fill("users_active", "SELECT day, COUNT(*) FROM daily_activity WHERE day BETWEEN ? AND ? GROUP BY day", S, E)
        fill("users_returned", "SELECT a.day, COUNT(*) FROM daily_activity a JOIN users u ON u.tg_id = a.user_id "
                               "WHERE a.day BETWEEN ? AND ? AND substr(u.created_at,1,10) < a.day GROUP BY a.day", S, E)
        fill("revenue", f"SELECT substr(p.paid_at,1,10), SUM(p.amount_stars) FROM payments p WHERE {REAL} AND substr(p.paid_at,1,10) BETWEEN ? AND ? GROUP BY 1", S, E)
        fill("purchases", f"SELECT substr(p.paid_at,1,10), COUNT(*) FROM payments p WHERE {REAL} AND substr(p.paid_at,1,10) BETWEEN ? AND ? GROUP BY 1", S, E)
        for kind in ("photo", "video", "audio"):
            fill(kind, "SELECT substr(created_at,1,10), COUNT(*) FROM orders WHERE kind = ? AND substr(created_at,1,10) BETWEEN ? AND ? GROUP BY 1", kind, S, E)
        for key, reason, sign in (("tokens_spent", "order_charge", -1), ("tokens_refunded", "order_refund", 1)):
            for d, n in c.execute("SELECT substr(created_at,1,10), SUM(delta) FROM credit_ledger WHERE reason = ? AND substr(created_at,1,10) BETWEEN ? AND ? GROUP BY 1", (reason, S, E)):
                if d in out[key]:
                    out[key][d] += (n or 0) * sign
        for d, n in c.execute("SELECT substr(l.created_at,1,10), SUM(l.delta) FROM credit_ledger l JOIN payments p ON p.id = l.payment_id "
                              "WHERE l.reason = 'purchase' AND p.provider != 'test' AND substr(l.created_at,1,10) BETWEEN ? AND ? GROUP BY 1", (S, E)):
            if d in out["tokens_bought"]:
                out["tokens_bought"][d] += n or 0
    res: dict = {"days": days}
    for k, v in out.items():
        res[k] = [v[d] for d in days]
    res["generations"] = [a + b + c for a, b, c in zip(res["photo"], res["video"], res["audio"])]
    res["avg_check"] = [round(r / p, 1) if p else 0 for r, p in zip(res["revenue"], res["purchases"])]
    return res


def retention(db: Database, days: int = 30) -> dict:
    """Удержание: доля пользователей когорты (по дню регистрации), вернувшихся ровно на N-й день."""
    t = today()
    start = t - timedelta(days=days - 1)
    steps = (1, 3, 7, 14, 30)
    with db.read() as c:
        sizes = {r[0]: r[1] for r in c.execute("SELECT substr(created_at,1,10), COUNT(*) FROM users WHERE substr(created_at,1,10) BETWEEN ? AND ? GROUP BY 1", (start.isoformat(), t.isoformat()))}
        got: dict[int, dict] = {}
        for n in steps:
            got[n] = {r[0]: r[1] for r in c.execute(
                "SELECT substr(u.created_at,1,10) AS cd, COUNT(DISTINCT a.user_id) FROM users u JOIN daily_activity a "
                "ON a.user_id = u.tg_id AND a.day = date(substr(u.created_at,1,10), ?) "
                "WHERE substr(u.created_at,1,10) BETWEEN ? AND ? GROUP BY cd", (f"+{n} days", start.isoformat(), t.isoformat()))}
    rows, tot = [], {n: [0, 0] for n in steps}
    for d in sorted(sizes, reverse=True):
        size = sizes[d]
        row = {"day": d, "size": size}
        for n in steps:
            if date.fromisoformat(d) + timedelta(days=n) > t:
                row[f"d{n}"] = None
            else:
                kept = got[n].get(d, 0)
                row[f"d{n}"] = {"pct": _pct(kept, size), "count": kept}
                tot[n][0] += kept
                tot[n][1] += size
        rows.append(row)
    return {"rows": rows, "average": {f"d{n}": _pct(a, b) for n, (a, b) in tot.items()},
            "note": "Удержание считается по ежедневной активности и накапливается с момента обновления; для пользователей, "
                    "созданных раньше, известны только день регистрации и последний вход."}


def funnel(db: Database, s: date, e: date) -> dict:
    S, E = s.isoformat(), e.isoformat()
    with db.read() as c:
        cohort = "SELECT tg_id FROM users WHERE substr(created_at,1,10) BETWEEN ? AND ?"
        q = lambda sql: c.execute(sql, (S, E)).fetchone()[0]
        stages = [
            ("Запустил бота", q(f"SELECT COUNT(DISTINCT user_id) FROM events WHERE name = 'bot_started' AND user_id IN ({cohort})")),
            ("Открыл Mini App", q(f"SELECT COUNT(DISTINCT user_id) FROM events WHERE name = 'miniapp_opened' AND user_id IN ({cohort})")),
            ("Создал первую генерацию", q(f"SELECT COUNT(*) FROM (SELECT user_id FROM orders WHERE user_id IN ({cohort}) GROUP BY user_id HAVING COUNT(*) >= 1)")),
            ("Создал вторую генерацию", q(f"SELECT COUNT(*) FROM (SELECT user_id FROM orders WHERE user_id IN ({cohort}) GROUP BY user_id HAVING COUNT(*) >= 2)")),
            ("Купил токены", q(f"SELECT COUNT(DISTINCT user_id) FROM payments WHERE status = 'paid' AND provider = 'stars' AND user_id IN ({cohort})")),
            ("Оформил PRO", q("SELECT COUNT(*) FROM users WHERE is_pro = 1 AND substr(created_at,1,10) BETWEEN ? AND ?")),
        ]
        total = q("SELECT COUNT(*) FROM users WHERE substr(created_at,1,10) BETWEEN ? AND ?")
    out, prev = [], None
    for name, n in stages:
        out.append({"stage": name, "count": n, "of_prev": _pct(n, prev) if prev is not None else None, "of_total": _pct(n, total)})
        prev = n
    return {"cohort_size": total, "stages": out,
            "note": "Воронка по пользователям, зарегистрированным в выбранный период. События «запуск бота» и «открытие Mini App» собираются с момента обновления."}


def popularity(db: Database, s: date, e: date) -> dict:
    S, E = s.isoformat(), e.isoformat()
    base = ("COUNT(o.id) AS uses, COUNT(DISTINCT o.user_id) AS users, COALESCE(SUM(o.price_credits),0) AS credits, "
            "SUM(o.status = 'done') AS ok, SUM(o.status IN ('done','failed')) AS finished")
    where = "substr(o.created_at,1,10) BETWEEN ? AND ?"
    out = {}
    with db.read() as c:
        def run(name, select_group):
            rows = [dict(r) for r in c.execute(select_group, (S, E)).fetchall()]
            for r in rows:
                r["success_rate"] = _pct(r.pop("ok") or 0, r.pop("finished") or 0)
            out[name] = rows
        run("categories", f"SELECT COALESCE(c.title, 'Без категории') AS name, {base} FROM orders o JOIN templates t ON t.id = o.template_id "
                          f"LEFT JOIN categories c ON c.id = t.category WHERE {where} AND t.is_system = 0 GROUP BY t.category ORDER BY uses DESC LIMIT 50")
        run("styles", f"SELECT COALESCE(NULLIF(t.style_label,''), 'Без стиля') AS name, {base} FROM orders o JOIN templates t ON t.id = o.template_id "
                      f"WHERE {where} AND t.is_system = 0 GROUP BY name ORDER BY uses DESC LIMIT 50")
        run("templates", f"SELECT t.title AS name, {base} FROM orders o JOIN templates t ON t.id = o.template_id "
                         f"WHERE {where} AND t.is_system = 0 GROUP BY t.id ORDER BY uses DESC LIMIT 50")
        free = c.execute(f"SELECT COUNT(*) AS uses, COUNT(DISTINCT o.user_id) AS users, COALESCE(SUM(o.price_credits),0) AS credits, "
                         f"SUM(o.status = 'done') AS ok, SUM(o.status IN ('done','failed')) AS finished FROM orders o JOIN templates t ON t.id = o.template_id "
                         f"WHERE {where} AND t.is_system = 1", (S, E)).fetchone()
    out["freeform"] = {"name": "Свободная генерация (по описанию)", "uses": free["uses"], "users": free["users"], "credits": free["credits"],
                       "success_rate": _pct(free["ok"] or 0, free["finished"] or 0)}
    return out


def providers(db: Database, s: date, e: date) -> list[dict]:
    S, E = s.isoformat(), e.isoformat()
    with db.read() as c:
        rows = [dict(r) for r in c.execute(
            "SELECT COALESCE(o.model, t.model) AS model, COUNT(*) AS generations, SUM(o.status = 'done') AS ok, SUM(o.status = 'failed') AS errors, "
            "AVG(CASE WHEN o.status = 'done' AND o.started_at IS NOT NULL AND o.finished_at IS NOT NULL THEN (julianday(o.finished_at) - julianday(o.started_at)) * 86400 END) AS avg_seconds, "
            "COALESCE(SUM(o.provider_cost_usd),0) AS cost_usd, COALESCE(SUM(o.price_credits),0) AS credits "
            "FROM orders o JOIN templates t ON t.id = o.template_id WHERE substr(o.created_at,1,10) BETWEEN ? AND ? GROUP BY 1 ORDER BY generations DESC", (S, E))]
    for r in rows:
        r["success_rate"] = _pct(r["ok"] or 0, (r["ok"] or 0) + (r["errors"] or 0))
        r["avg_seconds"] = round(r["avg_seconds"], 1) if r["avg_seconds"] is not None else None
        r["cost_usd"] = round(r["cost_usd"], 4)
        r["cost_per_generation"] = round(r["cost_usd"] / r["ok"], 4) if r["ok"] else None
    return rows


def bot_stats(db: Database, s: date, e: date) -> dict:
    S, E = s.isoformat(), e.isoformat()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
    with db.read() as c:
        one = lambda sql, *a: c.execute(sql, a).fetchone()[0]
        cmds = {r[0]: r[1] for r in c.execute(
            "SELECT json_extract(props, '$.cmd'), COUNT(*) FROM events WHERE name = 'bot_command' AND substr(ts,1,10) BETWEEN ? AND ? GROUP BY 1", (S, E))}
        return {
            "start": one("SELECT COUNT(*) FROM events WHERE name = 'bot_started' AND substr(ts,1,10) BETWEEN ? AND ?", S, E),
            "start_users": one("SELECT COUNT(DISTINCT user_id) FROM events WHERE name = 'bot_started' AND substr(ts,1,10) BETWEEN ? AND ?", S, E),
            "miniapp": one("SELECT COUNT(*) FROM events WHERE name = 'miniapp_opened' AND substr(ts,1,10) BETWEEN ? AND ?", S, E),
            "miniapp_users": one("SELECT COUNT(DISTINCT user_id) FROM events WHERE name = 'miniapp_opened' AND substr(ts,1,10) BETWEEN ? AND ?", S, E),
            "commands": {k: cmds.get(k, 0) for k in ("create", "profile", "history", "settings")},
            "returned": one("SELECT COUNT(DISTINCT a.user_id) FROM daily_activity a JOIN users u ON u.tg_id = a.user_id "
                            "WHERE a.day BETWEEN ? AND ? AND substr(u.created_at,1,10) < ?", S, E, S),
            "churned": one("SELECT COUNT(*) FROM users u WHERE u.last_seen_at < ? AND (SELECT COUNT(*) FROM daily_activity a WHERE a.user_id = u.tg_id) >= 2", cutoff),
            "note": "«Перестали пользоваться» — пользователи с хотя бы двумя днями активности, не заходившие более 14 дней. "
                    "События бота и Mini App собираются с момента обновления.",
        }


def tokens_flow(db: Database, s: date, e: date) -> dict:
    ov = overview(db, s, e, 0)
    with db.read() as c:
        total = {r["reason"]: r["s"] or 0 for r in c.execute("SELECT reason, SUM(delta) AS s FROM credit_ledger GROUP BY reason")}
        total["purchase"] = c.execute("SELECT COALESCE(SUM(l.delta),0) FROM credit_ledger l JOIN payments p ON p.id = l.payment_id "
                                      "WHERE l.reason = 'purchase' AND p.provider != 'test'").fetchone()[0]
    return {"period": ov["tokens"], "all_time": {
        "sold": total.get("purchase", 0), "spent": -total.get("order_charge", 0), "refunded": total.get("order_refund", 0),
        "bonus": total.get("welcome_bonus", 0) + total.get("purchase_bonus", 0), "admin": total.get("admin_adjust", 0),
        "balance_total": ov["tokens"]["balance_total"]}}


def revenue_report(db: Database, s: date, e: date, star_rate: float) -> dict:
    S, E = s.isoformat(), e.isoformat()
    ov = overview(db, s, e, star_rate)
    with db.read() as c:
        users_total = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        payers = c.execute(f"SELECT COUNT(DISTINCT p.user_id) FROM payments p WHERE {REAL} AND substr(p.paid_at,1,10) BETWEEN ? AND ?", (S, E)).fetchone()[0]
        all_time = _n(c.execute(f"SELECT SUM(p.amount_stars) FROM payments p WHERE {REAL}").fetchone()[0])
        payers_all = c.execute(f"SELECT COUNT(DISTINCT p.user_id) FROM payments p WHERE {REAL}").fetchone()[0]
        by_product = [dict(r) for r in c.execute(
            f"SELECT k.title AS name, COUNT(*) AS purchases, SUM(p.amount_stars) AS revenue FROM payments p JOIN packages k ON k.id = p.package_id "
            f"WHERE {REAL} AND substr(p.paid_at,1,10) BETWEEN ? AND ? GROUP BY k.id ORDER BY revenue DESC", (S, E))]
        by_method = [dict(r) for r in c.execute(
            "SELECT provider AS method, currency, COUNT(*) AS purchases, SUM(amount) AS revenue FROM payments "
            "WHERE status = 'paid' AND provider != 'test' AND substr(paid_at,1,10) BETWEEN ? AND ? GROUP BY provider, currency", (S, E))]
    rev = ov["money"]["revenue_stars"]
    return {"money": ov["money"], "all_time_stars": all_time, "arpu": round(rev / users_total, 2) if users_total else 0,
            "arppu": round(rev / payers, 2) if payers else 0, "payers": payers, "payers_all_time": payers_all,
            "conversion": _pct(payers_all, users_total), "by_product": by_product, "by_method": by_method, "by_tariff": [],
            "note": "Выручка считается в Telegram Stars (реальные платежи, тестовые не входят); пересчёт в USD — приблизительный, по курсу из настроек. "
                    "Выручки по тарифам нет: подписки пока назначаются вручную."}


def bot_stats(db: Database, s: date, e: date) -> dict:
    """Отдельно по боту: пользователи, генерации по типам, ошибки. Всё из той же базы, что и приложение."""
    S, E = s.isoformat(), e.isoformat()
    with db.read() as c:
        one = lambda sql, *a: c.execute(sql, a).fetchone()[0]
        kinds = {r["kind"]: r["n"] for r in c.execute(
            "SELECT kind, COUNT(*) AS n FROM orders WHERE source = 'bot' AND substr(created_at,1,10) BETWEEN ? AND ? GROUP BY kind", (S, E))}
        total_kinds = {r["kind"]: r["n"] for r in c.execute("SELECT kind, COUNT(*) AS n FROM orders WHERE source = 'bot' GROUP BY kind")}
        return {
            "users_total": one("SELECT COUNT(DISTINCT user_id) FROM orders WHERE source = 'bot'"),
            "users_period": one("SELECT COUNT(DISTINCT user_id) FROM orders WHERE source = 'bot' AND substr(created_at,1,10) BETWEEN ? AND ?", S, E),
            "started": one("SELECT COUNT(DISTINCT user_id) FROM events WHERE name = 'bot_started'"),
            "started_period": one("SELECT COUNT(DISTINCT user_id) FROM events WHERE name = 'bot_started' AND substr(ts,1,10) BETWEEN ? AND ?", S, E),
            "generations_period": sum(kinds.values()),
            "generations_total": sum(total_kinds.values()),
            "photo": kinds.get("photo", 0), "video": kinds.get("video", 0), "audio": kinds.get("audio", 0),
            "errors_period": one("SELECT COUNT(*) FROM orders WHERE source = 'bot' AND status = 'failed' AND substr(created_at,1,10) BETWEEN ? AND ?", S, E),
            "last_activity": one("SELECT MAX(created_at) FROM orders WHERE source = 'bot'") or
                             one("SELECT MAX(ts) FROM events WHERE name = 'bot_started'"),
            "app": {
                "users_total": one("SELECT COUNT(DISTINCT user_id) FROM orders WHERE source = 'app'"),
                "generations_period": one("SELECT COUNT(*) FROM orders WHERE source = 'app' AND substr(created_at,1,10) BETWEEN ? AND ?", S, E),
            },
        }
