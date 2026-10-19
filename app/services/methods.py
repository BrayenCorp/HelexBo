"""Способы оплаты. Администратор задаёт статус (on / soon / off), но пользователю способ показывается как
рабочий ТОЛЬКО если он технически подключён. Нерабочие способы не показываются как рабочие."""
from __future__ import annotations

from ..config import Settings
from ..db import Database
from ..errors import DomainError

# Технические возможности проекта: что реально умеет принять платёж.
def is_ready(code: str, settings: Settings, bot_present: bool) -> bool:
    if code == "stars":
        return settings.payments_mode == "stars" and bot_present
    if code == "test":
        return settings.payments_mode == "test"
    return False  # СБП, банковская карта и др.: нужен платёжный провайдер, в проекте он не подключён


def _rows(db: Database) -> list[dict]:
    with db.read() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM payment_methods ORDER BY sort_order, code").fetchall()]


def for_users(db: Database, settings: Settings, bot_present: bool) -> dict:
    available, soon = [], []
    for m in _rows(db):
        item = {"code": m["code"], "title": m["title"], "description": m["description"]}
        if m["status"] == "on" and is_ready(m["code"], settings, bot_present):
            available.append(item)
        elif m["status"] == "soon" and not is_ready(m["code"], settings, bot_present):
            soon.append(item)
    return {"available": available, "soon": soon}


def is_available(db: Database, settings: Settings, bot_present: bool, code: str) -> bool:
    return any(m["code"] == code for m in for_users(db, settings, bot_present)["available"])


def admin_list(db: Database, settings: Settings, bot_present: bool) -> list[dict]:
    with db.read() as conn:
        stats = {r["provider"]: r for r in conn.execute(
            "SELECT provider, COUNT(*) AS payments, SUM(CASE WHEN status = 'paid' THEN 1 ELSE 0 END) AS paid, "
            "SUM(CASE WHEN status IN ('failed', 'cancelled') THEN 1 ELSE 0 END) AS errors, "
            "SUM(CASE WHEN status = 'paid' THEN amount ELSE 0 END) AS revenue, MAX(currency) AS currency FROM payments GROUP BY provider").fetchall()}
    out = []
    for m in _rows(db):
        st = stats.get(m["code"])
        out.append({**m, "ready": is_ready(m["code"], settings, bot_present),
                    "payments": st["payments"] if st else 0, "paid": (st["paid"] or 0) if st else 0,
                    "errors": (st["errors"] or 0) if st else 0, "revenue": (st["revenue"] or 0) if st else 0,
                    "currency": st["currency"] if st else ""})
    return out


def update(db: Database, code: str, fields: dict) -> dict:
    sets, args = [], []
    if "status" in fields:
        if fields["status"] not in ("on", "soon", "off"):
            raise DomainError("Неизвестный статус")
        sets.append("status = ?"); args.append(fields["status"])
    if "fee_percent" in fields:
        raw = fields["fee_percent"]
        try:
            fee = None if raw in (None, "") else float(raw)
        except (TypeError, ValueError):
            raise DomainError("Комиссия должна быть числом")
        if fee is not None and not 0 <= fee <= 100:
            raise DomainError("Комиссия — от 0 до 100 %")
        sets.append("fee_percent = ?"); args.append(fee)
    for key in ("title", "description"):
        if key in fields:
            sets.append(f"{key} = ?"); args.append(str(fields[key]).strip()[:200])
    with db.tx() as conn:
        if conn.execute("SELECT 1 FROM payment_methods WHERE code = ?", (code,)).fetchone() is None:
            raise DomainError("Способ оплаты не найден", code="not_found", status=404)
        if sets:
            conn.execute(f"UPDATE payment_methods SET {', '.join(sets)} WHERE code = ?", [*args, code])
        return dict(conn.execute("SELECT * FROM payment_methods WHERE code = ?", (code,)).fetchone())
