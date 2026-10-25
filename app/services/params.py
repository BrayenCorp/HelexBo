"""Параметры свободного генератора: проверка значений и перевод в текст для промпта."""
from __future__ import annotations

import json

from ..errors import DomainError

MAX_PROMPT = 500

FORMATS = {"1:1": "square 1:1", "3:4": "portrait 3:4", "4:3": "landscape 4:3", "9:16": "vertical 9:16", "16:9": "wide 16:9", "21:9": "ultrawide 21:9"}
RESOLUTIONS = {"1k": "", "2k": "", "4k": "", "480p": "", "720p": "", "1080p": ""}
DURATIONS = {"5": "", "8": "", "10": "", "15": "", "30": "", "60": ""}
VOICES = {"alina": "", "maxim": "", "olga": "", "igor": "", "sofia": ""}
EMOTIONS = {"neutral": "", "joy": "", "calm": "", "solemn": "", "sad": "", "inspire": ""}
TONES = {"even": "", "question": "", "exclaim": "", "confidential": "", "ad": ""}
MAX_AUDIO_TEXT = 2000
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

_ALLOWED = {"format": FORMATS, "quality": QUALITIES, "style": STYLES, "lighting": LIGHTING, "camera": CAMERAS, "resolution": RESOLUTIONS,
            "duration": DURATIONS, "voice": VOICES, "emotion": EMOTIONS, "tone": TONES}


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
        if key == "duration":
            value = str(value)
        if value not in options:
            raise DomainError(f"Недопустимое значение параметра «{key}»", code="bad_params")
        out[key] = value
    seed = raw.get("seed")
    if seed not in (None, ""):
        try:
            seed = int(seed)
        except (TypeError, ValueError):
            raise DomainError("Случайное зерно — целое число", code="bad_params")
        if not 0 <= seed <= 2**31 - 1:
            raise DomainError("Случайное зерно — число от 0 до 2147483647", code="bad_params")
        out["seed"] = seed
    speed = raw.get("speed")
    if speed not in (None, ""):
        try:
            speed = round(float(speed), 2)
        except (TypeError, ValueError):
            raise DomainError("Скорость — число от 0,5 до 2", code="bad_params")
        if not 0.5 <= speed <= 2.0:
            raise DomainError("Скорость — число от 0,5 до 2", code="bad_params")
        out["speed"] = speed
    negative = str(raw.get("negative") or "").strip()
    if negative:
        out["negative"] = negative[:200]
    return out


def params_to_prompt(params: dict) -> str:
    parts = [
        STYLES.get(params.get("style", ""), ""), LIGHTING.get(params.get("lighting", ""), ""),
        CAMERAS.get(params.get("camera", ""), ""), QUALITIES.get(params.get("quality", ""), ""),
    ]
    if params.get("format"):
        parts.append(f"aspect ratio {params['format']}")
    if params.get("negative"):
        parts.append(f"avoid: {params['negative']}")
    return ", ".join(p for p in parts if p)


def clean_prompt(text, limit: int = MAX_PROMPT) -> str:
    text = (text or "").strip()
    if len(text) > limit:
        raise DomainError(f"Текст длиннее {limit} символов", code="prompt_too_long")
    return text
