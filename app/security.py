"""Проверка Telegram WebApp initData на сервере и роли администраторов."""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl

from .errors import InvalidInitData


def validate_init_data(init_data: str, bot_token: str, *, max_age: int = 86400, now: float | None = None) -> dict:
    """Алгоритм из документации Telegram: HMAC-SHA256 с ключом HMAC("WebAppData", bot_token).

    Возвращает {"id", "username", "first_name"} только если подпись верна и данные не устарели.
    """
    if not init_data or not bot_token:
        raise InvalidInitData("Нет данных авторизации Telegram")
    data = dict(parse_qsl(init_data, keep_blank_values=True))
    received = data.pop("hash", None)
    if not received:
        raise InvalidInitData("В данных нет подписи")
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received):
        raise InvalidInitData("Подпись не совпадает")
    try:
        auth_date = int(data["auth_date"])
    except (KeyError, ValueError):
        raise InvalidInitData("Нет даты авторизации")
    current = time.time() if now is None else now
    if current - auth_date > max_age or auth_date - current > 300:
        raise InvalidInitData("Данные авторизации устарели — откройте приложение заново")
    try:
        user = json.loads(data["user"])
        tg_id = int(user["id"])
    except (KeyError, ValueError, TypeError):
        raise InvalidInitData("В данных нет пользователя")
    return {"id": tg_id, "username": user.get("username"), "first_name": user.get("first_name"),
            "last_name": user.get("last_name"), "language_code": user.get("language_code"), "photo_url": user.get("photo_url"),
            "start_param": data.get("start_param")}


@dataclass(frozen=True)
class AdminAccess:
    """Доступ только для заранее указанных Telegram ID (переменные OWNER_IDS и DEVELOPER_IDS)."""

    owner_ids: frozenset[int] = frozenset()
    developer_ids: frozenset[int] = frozenset()

    def roles(self, tg_id: int) -> list[str]:
        roles = []
        if tg_id in self.owner_ids:
            roles.append("owner")
        if tg_id in self.developer_ids:
            roles.append("developer")
        return roles
