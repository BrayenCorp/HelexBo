"""Параметры свободного генератора: проверка значений и перевод в текст для промпта."""
from __future__ import annotations

import json

from ..errors import DomainError

MAX_PROMPT = 500

FORMATS = {"1:1": "square 1:1", "3:4": "portrait 3:4", "4:3": "landscape 4:3", "9:16": "vertical 9:16", "16:9": "wide 16:9"}
QUALITIES = {"standard": "", "high": "high detail, sharp, premium quality"}
STYLES = {
    "realistic": "photorealistic", "cinematic": "cinematic look", "luxury": "luxury editorial look",
    "studio": "studio photography", "street": "street photography", "anime": "anime illustration", "portrait": "portrait photography",
}
LIGHTING = {
    "natural": "natural daylight", "studio": "studio lighting", "soft": "soft diffused light",
    "contrast": "dramatic contrast lighting", "sunset": "golden hour sunset light",
}
CAMERAS = {"portrait": "85mm portrait lens", "wide": "wide-angle lens", "closeup": "close-up shot", "topdown": "top-down view"}

_ALLOWED = {"format": FORMATS, "quality": QUALITIES, "style": STYLES, "lighting": LIGHTING, "camera": CAMERAS}


def clean_params(raw) -> dict:
    """Оставляет только известные параметры с допустимыми значениями; неизвестные поля отбрасывает."""
    if raw in (None, "", {}):
        return {}
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            raise DomainError("Некорректные параметры генерации", code="bad_params")
    if not isinstance(raw, dict):
        raise DomainError("Некорректные параметры генерации", code="bad_params")
    out: dict = {}
    for key, options in _ALLOWED.items():
        value = raw.get(key)
        if value in (None, ""):
            continue
        if value not in options:
            raise DomainError(f"Недопустимое значение параметра «{key}»", code="bad_params")
        out[key] = value
    return out


def params_to_prompt(params: dict) -> str:
    parts = [
        STYLES.get(params.get("style", ""), ""), LIGHTING.get(params.get("lighting", ""), ""),
        CAMERAS.get(params.get("camera", ""), ""), QUALITIES.get(params.get("quality", ""), ""),
    ]
    if params.get("format"):
        parts.append(f"aspect ratio {params['format']}")
    return ", ".join(p for p in parts if p)


def clean_prompt(text) -> str:
    text = (text or "").strip()
    if len(text) > MAX_PROMPT:
        raise DomainError(f"Описание длиннее {MAX_PROMPT} символов", code="prompt_too_long")
    return text
