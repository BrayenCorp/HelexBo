"""Точка запуска Nolla AI: один процесс = API + Mini App (статика) + Telegram-бот."""
from __future__ import annotations

import asyncio
import logging

import uvicorn

from .ai.registry import ProviderRegistry
from .api import create_app
from .config import Settings
from .context import AppContext
from .db import Database, init_db
from .runner import Runner
from .security import AdminAccess
from .services import orders, showcase_sync
from .storage import Storage

log = logging.getLogger("studio")


async def amain() -> None:
    settings = Settings.from_env()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    db = Database(settings.database_path)
    init_db(db)
    from .seed import apply_welcome_default

    apply_welcome_default(db, settings.welcome_bonus)
    showcase_sync.sync(db)  # витрина берётся из app/showcase.py
    storage = Storage(settings.data_dir)
    providers = ProviderRegistry(settings.ai_mode, settings.image_api_key, settings.video_api_key, settings.seedance_api_key, settings.audio_api_key, settings.demo_delay)
    runner = Runner(db, storage, providers, max_parallel=settings.max_parallel_generations, timeout=settings.generation_timeout,
                    ai_mode=settings.ai_mode, demo_delay=settings.demo_delay)
    ctx = AppContext(settings, db, storage, providers, runner, AdminAccess(settings.owner_ids, settings.developer_ids))

    from .services import avatars as avatars_service

    avatars_service.fail_unfinished(db)
    closed = orders.fail_unfinished_orders(db, "Сервис был перезапущен во время генерации")
    if closed:
        log.warning("Закрыто %s зависших заказов (кредиты возвращены)", closed)

    from .version import BUILD, webapp_state

    state, detail = webapp_state(settings.webapp_dist)
    log.info("Код сервера: сборка %s", BUILD)
    (log.info if state == "ok" else log.error)("Mini App: %s", detail)

    if settings.ai_mode == "mock":
        log.warning("AI_MODE=mock: результаты — ТЕСТОВЫЕ заглушки, не настоящая генерация")
    if settings.payments_mode == "test":
        log.warning("PAYMENTS_MODE=test: оплата тестовая, реальные деньги не принимаются")
    if settings.dev_mode:
        log.warning("DEV_MODE=1: вход без Telegram включён — НЕ используйте на публичном сервере")
    if not settings.owner_ids and not settings.developer_ids:
        log.warning("OWNER_IDS/DEVELOPER_IDS пусты: админ-панель никому не доступна")

    poll_task = None
    bot = None
    if settings.bot_token:
        from .bot import BotNotifier, build_bot, setup_bot_profile

        bot, dp = build_bot(ctx)
        ctx.bot = bot
        try:
            ctx.bot_username = (await bot.get_me()).username or ""
        except Exception:
            log.warning("Не удалось получить имя бота — «Поделиться» отправит только текст")
        runner.notifier = BotNotifier(bot, ctx)
        await setup_bot_profile(bot, ctx)
        poll_task = asyncio.create_task(dp.start_polling(bot, handle_signals=False))
        log.info("Telegram-бот запущен")
    else:
        log.warning("BOT_TOKEN не задан: запущен только API (бот и вход через Telegram недоступны)")

    server = uvicorn.Server(uvicorn.Config(create_app(ctx), host=settings.host, port=settings.port, log_level="info"))
    try:
        await server.serve()
    finally:
        if poll_task:
            poll_task.cancel()
        if bot:
            await bot.session.close()


def main() -> None:
    asyncio.run(amain())


if __name__ == "__main__":
    main()
