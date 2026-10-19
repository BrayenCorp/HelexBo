"""События продукта. Пишем только то, чего нет в других таблицах (старт бота, открытие Mini App, команды,
вход, PRO, действия админов). События генераций, платежей и токенов не дублируются: они считаются
из заказов, платежей и журнала токенов — так цифры всегда совпадают."""
from __future__ import annotations

import json

from ..db import Database, now

# Код события → название на русском (в стиле ТЗ). Для производных событий указан источник данных.
LABELS = {
    "user_registered": "ПОЛЬЗОВАТЕЛЬ_ЗАРЕГИСТРИРОВАЛСЯ",
    "bot_started": "БОТ_ЗАПУЩЕН",
    "miniapp_opened": "MINI_APP_ОТКРЫТ",
    "bot_command": "КОМАНДА_БОТА",
    "pro_enabled": "PRO_ПОДКЛЮЧЕН",
    "pro_cancelled": "PRO_ОТМЕНЁН",
    "admin_action": "ДЕЙСТВИЕ_АДМИНИСТРАТОРА",
}
DERIVED = {  # события, которые считаются из других таблиц
    "ГЕНЕРАЦИЯ_НАЧАТА / ЗАВЕРШЕНА / ОШИБКА": "заказы (orders)",
    "ФОТО_СОЗДАНО / ВИДЕО_СОЗДАНО": "заказы со статусом «готово»",
    "КРЕДИТЫ_КУПЛЕНЫ": "платежи (payments)",
    "КРЕДИТЫ_ПОТРАЧЕНЫ / ВОЗВРАЩЕНЫ": "журнал токенов (credit_ledger)",
}


def log_conn(conn, name: str, user_id: int | None = None, **props) -> None:
    conn.execute("INSERT INTO events (ts, user_id, name, props) VALUES (?, ?, ?, ?)",
                 (now(), user_id, name, json.dumps(props, ensure_ascii=False)))


def log(db: Database, name: str, user_id: int | None = None, **props) -> None:
    with db.tx() as conn:
        log_conn(conn, name, user_id, **props)
