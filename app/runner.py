"""Фоновый запуск генераций. Один Runner на процесс — и для бота, и для API."""
from __future__ import annotations

import asyncio
import logging
from typing import Protocol

from .ai.registry import ProviderRegistry
from .db import Database
from .services import generation, orders
from .storage import Storage

log = logging.getLogger(__name__)


class Notifier(Protocol):
    async def notify_order(self, order: dict, with_menu: bool = True) -> None: ...


class Runner:
    def __init__(
        self, db: Database, storage: Storage, providers: ProviderRegistry,
        notifier: Notifier | None = None, max_parallel: int = 3, timeout: int = 600,
        ai_mode: str = "mock", demo_delay: float = 0.0,
    ):
        self.db, self.storage, self.providers = db, storage, providers
        self.notifier = notifier
        self.timeout = timeout
        self.ai_mode, self.demo_delay = ai_mode, demo_delay
        self._sem = asyncio.Semaphore(max_parallel)
        self._tasks: set[asyncio.Task] = set()

    def schedule(self, order_id: int) -> asyncio.Task:
        task = asyncio.create_task(self._run(order_id))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    def schedule_avatar(self, avatar_id: int) -> asyncio.Task:
        from .services import avatars

        async def run() -> None:
            try:
                await asyncio.to_thread(avatars.process, self.db, self.storage, self.ai_mode, avatar_id, self.demo_delay)
            except Exception:
                log.exception("Сбой создания аватара %s", avatar_id)
                avatars._set(self.db, avatar_id, status="failed", error="Не получилось создать аватар. Попробуйте ещё раз.")

        task = asyncio.create_task(run())
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    def _wants_chat(self, order: dict) -> bool:
        from .services import users
        user = users.get_user(self.db, order["user_id"])
        return bool(user and user.get("notify_chat", 1))

    async def _run(self, order_id: int) -> None:
        order = None
        async with self._sem:
            try:
                order = await asyncio.wait_for(
                    asyncio.to_thread(generation.process_order, self.db, self.storage, self.providers, order_id),
                    timeout=self.timeout,
                )
            except asyncio.TimeoutError:
                orders.fail_order(self.db, order_id, "Превышено время ожидания генерации",
                                  "Генерация заняла слишком много времени. Попытка и токены возвращены.", error_type="timeout")
                order = orders.get_order(self.db, order_id)
            except Exception as e:
                log.exception("Сбой запуска заказа %s", order_id)
                orders.fail_order(self.db, order_id, f"{type(e).__name__}: {e}")
                order = orders.get_order(self.db, order_id)
        if order and self.notifier and self._wants_chat(order):
            try:
                await self.notifier.notify_order(order)
            except Exception:  # пользователь мог не запускать бота — не критично
                log.warning("Не удалось отправить результат заказа %s в чат", order_id, exc_info=True)
