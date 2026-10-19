"""Настройки из переменных окружения (файл .env). Секреты только здесь, во frontend они не попадают."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping


def _ids(raw: str) -> frozenset[int]:
    out: set[int] = set()
    for part in raw.replace(";", ",").split(","):
        part = part.strip()
        if part:
            out.add(int(part))
    return frozenset(out)


def _bool(raw: str) -> bool:
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    bot_token: str = ""
    webapp_url: str = ""
    host: str = "0.0.0.0"
    port: int = 8000
    data_dir: str = "data"
    database_path: str = "data/studio.db"
    webapp_dist: str = "webapp/dist"
    owner_ids: frozenset[int] = frozenset()
    developer_ids: frozenset[int] = frozenset()
    ai_mode: str = "mock"  # mock — тестовые заглушки, live — реальные API
    payments_mode: str = "test"  # test — тестовая оплата, stars — Telegram Stars, off — «оплата в разработке»
    dev_mode: bool = False  # вход без Telegram по заголовку X-Dev-User (только для локальной отладки!)
    init_data_max_age: int = 86400
    star_usd_rate: float = 0.013  # приблизительная выручка в USD за 1 Star — для оценки прибыли
    max_upload_mb: int = 10
    max_video_mb: int = 50  # видео-примеры для витрины и превью
    max_parallel_generations: int = 3
    generation_timeout: int = 600
    image_api_key: str = ""
    video_api_key: str = ""
    seedance_api_key: str = ""
    audio_api_key: str = ""
    demo_delay: float = 1.0  # секунд на этап в демо-режиме (имитация обработки); 0 — мгновенно
    welcome_bonus: int = 100  # стартовые демо-токены при обновлении, если бонус ещё не настраивали

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def max_video_bytes(self) -> int:
        return self.max_video_mb * 1024 * 1024

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        if env is None:
            from dotenv import load_dotenv

            load_dotenv()
            env = os.environ
        g = env.get
        data_dir = g("DATA_DIR", "data")
        s = cls(
            bot_token=g("BOT_TOKEN", ""),
            webapp_url=g("WEBAPP_URL", "").rstrip("/"),
            host=g("HOST", "0.0.0.0"),
            port=int(g("PORT", "8000")),
            data_dir=data_dir,
            database_path=g("DATABASE_PATH", f"{data_dir}/studio.db"),
            webapp_dist=g("WEBAPP_DIST", "webapp/dist"),
            owner_ids=_ids(g("OWNER_IDS", "")),
            developer_ids=_ids(g("DEVELOPER_IDS", "")),
            ai_mode=g("AI_MODE", "mock").strip().lower(),
            payments_mode=g("PAYMENTS_MODE", "test").strip().lower(),
            dev_mode=_bool(g("DEV_MODE", "0")),
            init_data_max_age=int(g("INIT_DATA_MAX_AGE", "86400")),
            star_usd_rate=float(g("STAR_USD_RATE", "0.013")),
            max_upload_mb=int(g("MAX_UPLOAD_MB", "10")),
            max_video_mb=int(g("MAX_VIDEO_MB", "50")),
            max_parallel_generations=int(g("MAX_PARALLEL_GENERATIONS", "3")),
            generation_timeout=int(g("GENERATION_TIMEOUT", "600")),
            image_api_key=g("IMAGE_API_KEY", ""),
            video_api_key=g("VIDEO_API_KEY", ""),
            seedance_api_key=g("SEEDANCE_API_KEY", ""),
            audio_api_key=g("AUDIO_API_KEY", ""),
            demo_delay=float(g("DEMO_DELAY", "1.0")),
            welcome_bonus=int(g("WELCOME_BONUS", "100")),
        )
        if s.ai_mode not in {"mock", "live"}:
            raise ValueError("AI_MODE должен быть mock или live")
        if s.payments_mode not in {"test", "stars", "off"}:
            raise ValueError("PAYMENTS_MODE должен быть test, stars или off")
        return s
