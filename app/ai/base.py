"""Общий интерфейс провайдеров генерации."""
from __future__ import annotations

from dataclasses import dataclass, field


class ProviderError(Exception):
    """Техническая ошибка провайдера — заказ провалится, кредиты вернутся."""


class ProviderNotConfigured(ProviderError):
    """Провайдер не подключён (нет ключа или интеграция — заглушка)."""


@dataclass(frozen=True)
class GenerationRequest:
    order_id: int
    kind: str  # photo | video
    model: str
    prompt: str
    title: str
    image: bytes  # очищенное JPEG-фото; пустые байты — генерация без фото
    params: dict = field(default_factory=dict)  # формат, качество и т. д. (уже добавлены в prompt текстом)


@dataclass(frozen=True)
class GenerationResult:
    data: bytes
    ext: str  # jpg | gif | mp4
    mime: str
    provider: str
    cost_usd: float = 0.0
    is_stub: bool = False  # True — это НЕ настоящая генерация
    duration_sec: int | None = None  # длительность видео


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
