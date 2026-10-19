"""Экспорт в CSV (кодировка UTF-8 с BOM — открывается в Excel с корректной кириллицей)."""
from __future__ import annotations

import csv
import io
from datetime import timedelta

from ..db import Database
from ..errors import DomainError
from . import admin_lists, admin_users, analytics

KINDS = {"users": "пользователи", "generations": "генерации", "payments": "платежи", "revenue": "выручка", "tokens": "токены",
         "referrals": "рефералы", "analytics": "аналитика"}
MAX_ROWS = 50_000


def _csv(headers: list[str], rows) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(headers)
    for r in rows:
        w.writerow(r)
    return ("\ufeff" + buf.getvalue()).encode("utf-8")


def _paged(fn, db, **kw):
    page, got = 1, 0
    while got < MAX_ROWS:
        res = fn(db, page=page, size=100, **kw)
        yield from res["items"]
        got += len(res["items"])
        if got >= res["total"] or not res["items"]:
            break
        page += 1


def build(db: Database, kind: str, star_rate: float, bot_username: str = "") -> tuple[str, bytes]:
    if kind not in KINDS:
        raise DomainError("Неизвестный тип экспорта", code="not_found", status=404)
    name = f"nolla-{kind}.csv"
    if kind == "users":
        rows = ((u["tg_id"], u["name"], u["username"] or "", u["created_at"], u["last_seen_at"] or "", u["tariff"], u["balance"], u["spent_stars"], u["spent_credits"],
                 u["generations"], u["photos"], u["videos"], u["source_label"], "заблокирован" if u["status"] == "blocked" else "активен")
                for u in _paged(admin_users.users_list, db))
        return name, _csv(["ID", "Имя", "Username", "Регистрация", "Последняя активность", "Тариф", "Баланс, токенов", "Потрачено, Stars",
                           "Потрачено токенов", "Генераций", "Фото", "Видео", "Источник", "Статус"], rows)
    if kind == "generations":
        rows = ((g["id"], g["user"], g["kind"], g["prompt"], g["category"] or "", g["template"], g["style_label"] or "", g["provider"], g["status_label"],
                 g["price_credits"], g["provider_cost_usd"], g["seconds"] if g["seconds"] is not None else "", g["created_at"]) for g in _paged(admin_lists.generations_list, db))
        return name, _csv(["ID", "Пользователь", "Тип", "Запрос", "Категория", "Шаблон", "Стиль", "Провайдер", "Статус", "Токены", "Стоимость, USD", "Время, сек", "Дата"], rows)
    if kind == "payments":
        rows = ((p["id"], p["user"], p["product"], p["amount"], p["currency"], p["credits"], p["bonus"], p["method"], p["status_label"], p["created_at"], p["paid_at"] or "")
                for p in _paged(admin_lists.payments_list, db))
        return name, _csv(["ID", "Пользователь", "Продукт", "Сумма", "Валюта", "Токены", "Бонус", "Способ", "Статус", "Создан", "Оплачен"], rows)
    if kind == "tokens":
        with db.read() as c:
            rows = [tuple(r) for r in c.execute("SELECT id, user_id, delta, reason, order_id, payment_id, COALESCE(note, ''), created_at FROM credit_ledger ORDER BY id DESC LIMIT ?", (MAX_ROWS,))]
        return name, _csv(["ID", "Пользователь", "Изменение", "Причина", "Заказ", "Платёж", "Примечание", "Дата"], rows)
    if kind == "referrals":
        res = admin_lists.referrals(db, bot_username)
        return name, _csv(["Пригласивший", "Ссылка", "Привлечено", "Активных", "Платящих", "Выручка, Stars", "Конверсия, %"],
                          ((r["name"], r["link"], r["invited"], r["active"], r["paying"], r["revenue"], r["conversion"] if r["conversion"] is not None else "") for r in res["items"]))
    t = analytics.today()
    days = 365 if kind == "revenue" else 90
    s = analytics.series(db, t - timedelta(days=days - 1), t)
    if kind == "revenue":
        return name, _csv(["Дата", "Выручка, Stars", "Покупок", "Средний чек, Stars"], zip(s["days"], s["revenue"], s["purchases"], s["avg_check"]))
    return name, _csv(["Дата", "Новые", "Активные", "Вернувшиеся", "Фото", "Видео", "Выручка, Stars", "Токенов куплено", "Токенов потрачено", "Токенов возвращено"],
                      zip(s["days"], s["users_new"], s["users_active"], s["users_returned"], s["photo"], s["video"], s["revenue"], s["tokens_bought"], s["tokens_spent"], s["tokens_refunded"]))
