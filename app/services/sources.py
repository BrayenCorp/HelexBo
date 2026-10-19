"""Источники пользователей. Источник определяется ТОЛЬКО из параметра запуска (?start=...), который
реально пришёл от Telegram. Если параметра нет — источник «Не определён», ничего не выдумываем.

Форматы параметра (разрешены латинские буквы, цифры, «_» и «-»):
  ref_<telegram_id>                  — реферальная ссылка пользователя
  src_<источник>[_<кампания>[_<материал>]]  — рекламная ссылка, например src_tiktok_spring_video1
"""
from __future__ import annotations

import re

KNOWN = {"telegram": "Telegram", "tiktok": "TikTok", "instagram": "Instagram", "youtube": "YouTube", "vk": "VK",
         "referral": "Реферальная ссылка", "direct": "Прямая ссылка"}
_SAFE = re.compile(r"[^a-z0-9\-]")


def label(source: str | None) -> str:
    if not source:
        return "Не определён"
    return KNOWN.get(source, source)


def parse_start_param(param: str | None, conn, tg_id: int) -> dict:
    """Возвращает {source, campaign, material, referrer_id}; пустой словарь, если определить нечего."""
    if not param:
        return {}
    param = param.strip()[:64]
    if param.startswith("ref_"):
        raw = param[4:]
        if raw.isdigit() and int(raw) != tg_id:
            if conn.execute("SELECT 1 FROM users WHERE tg_id = ?", (int(raw),)).fetchone():
                return {"source": "referral", "referrer_id": int(raw)}
        return {}
    if param.startswith("src_"):
        parts = param[4:].split("_", 2)
        clean = [_SAFE.sub("", p.lower())[:32] for p in parts]
        if clean and clean[0]:
            return {"source": clean[0], "campaign": clean[1] if len(clean) > 1 and clean[1] else None,
                    "material": clean[2] if len(clean) > 2 and clean[2] else None}
    return {}
