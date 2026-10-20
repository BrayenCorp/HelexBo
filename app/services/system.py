"""Состояние системы: бот, Mini App, база, AI API, платежи, очередь генераций."""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

OK, WARN, ERROR = "ok", "warn", "error"
_bot_cache: dict = {"ts": 0.0, "value": None}


async def _bot_status(ctx) -> dict:
    if not ctx.settings.bot_token:
        return {"code": "bot", "title": "Telegram-бот", "status": ERROR, "detail": "BOT_TOKEN не задан — бот не запущен."}
    if ctx.bot is None:
        return {"code": "bot", "title": "Telegram-бот", "status": ERROR, "detail": "Бот не инициализирован."}
    if time.time() - _bot_cache["ts"] > 60:  # не дёргаем Telegram чаще раза в минуту
        try:
            me = await ctx.bot.get_me()
            _bot_cache.update(ts=time.time(), value={"status": OK, "detail": f"Работает: @{me.username}"})
        except Exception as e:  # noqa: BLE001
            _bot_cache.update(ts=time.time(), value={"status": ERROR, "detail": f"Telegram API недоступен: {type(e).__name__}"})
    return {"code": "bot", "title": "Telegram-бот", **_bot_cache["value"]}


async def health(ctx) -> list[dict]:
    s, db = ctx.settings, ctx.db
    out = [await _bot_status(ctx)]
    dist = Path(s.webapp_dist) / "index.html"
    out.append({"code": "miniapp", "title": "Mini App", "status": OK if dist.exists() else ERROR,
                "detail": "Сборка найдена." if dist.exists() else "Сборка не найдена: выполните npm run build в папке webapp."})
    try:
        with db.read() as c:
            c.execute("SELECT 1").fetchone()
            users = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        size = os.path.getsize(db.path) / 1024 / 1024 if os.path.exists(db.path) else 0
        with db.read() as c:
            gens = c.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
            via_bot = c.execute("SELECT COUNT(*) FROM orders WHERE source = 'bot'").fetchone()[0]
        out.append({"code": "db", "title": "База данных", "status": OK,
                    "detail": f"Работает. Пользователей: {users}, генераций: {gens} (из них через бота: {via_bot}), размер файла: {size:.1f} МБ. Файл: {db.path}"})
        # На Railway база живёт только на подключённом томе: без него данные стираются при каждом деплое.
        volatile = not str(db.path).startswith("/data") and bool(os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RAILWAY_PROJECT_ID"))
        if volatile:
            out.append({"code": "storage", "title": "Хранилище", "status": ERROR,
                        "detail": "База лежит не на постоянном томе: при каждом деплое пользователи и генерации будут исчезать. "
                                  "Подключите Volume и задайте DATA_DIR=/data."})
    except Exception as e:  # noqa: BLE001
        out.append({"code": "db", "title": "База данных", "status": ERROR, "detail": f"Ошибка: {type(e).__name__}"})

    with db.read() as c:
        cut = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        total = c.execute("SELECT COUNT(*) FROM orders WHERE created_at >= ?", (cut,)).fetchone()[0]
        failed = c.execute("SELECT COUNT(*) FROM orders WHERE status = 'failed' AND created_at >= ?", (cut,)).fetchone()[0]
        pending = c.execute("SELECT COUNT(*), MIN(created_at) FROM orders WHERE status IN ('created', 'processing')").fetchone()
    rate = failed * 100 / total if total else 0
    desc = ctx.providers.describe()
    if s.ai_mode == "mock":
        ai = {"status": WARN, "detail": "Тестовый режим (AI_MODE=mock): результаты — заглушки, реальные AI-провайдеры не используются."}
    elif not any(p["configured"] and not p["stub"] for p in desc):
        ai = {"status": ERROR, "detail": "Нет подключённого AI-провайдера: ключи не заданы или интеграция не реализована."}
    elif total >= 5 and rate > 60:
        ai = {"status": ERROR, "detail": f"Высокая доля ошибок за 24 часа: {rate:.0f}%."}
    elif total >= 5 and rate > 30:
        ai = {"status": WARN, "detail": f"Повышенная доля ошибок за 24 часа: {rate:.0f}%."}
    else:
        ai = {"status": OK, "detail": "Провайдеры подключены."}
    out.append({"code": "ai", "title": "AI API", **ai})

    pm = {"stars": (OK, "Telegram Stars принимает платежи.") if (s.payments_mode == "stars" and ctx.bot) else None}
    if s.payments_mode == "off":
        pay = {"status": WARN, "detail": "Оплата отключена (PAYMENTS_MODE=off)."}
    elif s.payments_mode == "test":
        pay = {"status": WARN, "detail": "Тестовая оплата (PAYMENTS_MODE=test): реальные деньги не принимаются."}
    elif pm["stars"]:
        pay = {"status": OK, "detail": pm["stars"][1]}
    else:
        pay = {"status": ERROR, "detail": "PAYMENTS_MODE=stars, но бот не запущен — оплата недоступна."}
    out.append({"code": "payments", "title": "Платежи", **pay})

    n, oldest = pending[0], pending[1]
    age_min = ((datetime.now(timezone.utc) - datetime.fromisoformat(oldest)).total_seconds() / 60) if oldest else 0
    limit = s.generation_timeout / 60
    if n and age_min > limit * 2:
        q = {"status": ERROR, "detail": f"В очереди {n}, самая старая ждёт {age_min:.0f} мин. — возможно, обработка остановилась."}
    elif n and age_min > limit:
        q = {"status": WARN, "detail": f"В очереди {n}, самая старая ждёт {age_min:.0f} мин."}
    else:
        q = {"status": OK, "detail": f"В очереди: {n}." if n else "Очередь пуста."}
    out.append({"code": "queue", "title": "Очередь генераций", **q})
    return out
