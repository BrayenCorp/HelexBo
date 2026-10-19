"""Общий контекст приложения: передаётся и в API, и в бота."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .ai.registry import ProviderRegistry
from .config import Settings
from .db import Database
from .runner import Runner
from .security import AdminAccess
from .storage import Storage


@dataclass
class AppContext:
    settings: Settings
    db: Database
    storage: Storage
    providers: ProviderRegistry
    runner: Runner
    access: AdminAccess
    bot: Any = None  # aiogram.Bot, если задан BOT_TOKEN
    bot_username: str = ""  # для кнопки «Поделиться»
