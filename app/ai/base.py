"""Общий интерфейс провайдеров генерации."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


class ProviderError(Exception):
    """Техническая ошибка провайдера — заказ провалится, токены вернутся."""


class ProviderNotConfigured(ProviderError):
    """Провайдер не подключён (нет ключа или интеграция — заглушка)."""


@dataclass(frozen=True)
class GenerationRequest:
    order_id: int
    kind: str  # photo | video | audio
    model: str
    prompt: str
    title: str
    image: bytes  # очищенное JPEG-фото; пустые байты — генерация без фото
    params: dict = field(default_factory=dict)  # формат, качество и т. д. (уже добавлены в prompt текстом)
    image2: bytes = b""  # второе изображение: референс или одежда
    tool: str = ""  # особый инструмент: storyboard | angles | tryon | ...
    progress: Callable[[str], None] | None = None  # провайдер сообщает этапы: creating | processing | almost


@dataclass(frozen=True)
class GenerationResult:
    data: bytes
    ext: str  # jpg | gif | mp4 | wav
    mime: str
    provider: str
    cost_usd: float = 0.0
    is_stub: bool = False  # True — это НЕ настоящая генерация
    duration_sec: int | None = None  # длительность видео или аудио
    frames: tuple = ()  # ((подпись, jpeg-байты), ...) — кадры раскадровки / ракурсы


class Provider:
    name = "base"
    kind = "photo"

    @property
    def configured(self) -> bool:
        return True

    @property
    def is_stub(self) -> bool:
        return False

    def generate(self, req: GenerationRequest) -> GenerationResult:  # pragma: no cover - интерфейс
        raise NotImplementedError
