"""ЗАГЛУШКИ реальных API генерации (AI_MODE=live).

Здесь НЕТ выдуманных адресов и форматов запросов. Каждый класс — место, куда вы подключаете
настоящего провайдера, когда выберете его и получите ключ. Пока метод _call_api не написан,
генерация честно завершается ошибкой «не подключено», а кредиты/бесплатная попытка возвращаются.

Что нужно реализовать в _call_api(req) -> (bytes, ext, mime, cost_usd):
  1. отправить фото req.image и промпт req.prompt в API провайдера;
  2. для видео — дождаться окончания задачи (polling/webhook);
  3. скачать готовый файл и вернуть байты, расширение, mime и реальную стоимость в USD.
Секреты берите из переменных окружения (см. .env.example), логируйте только id задачи, не ключи.
"""
from __future__ import annotations

from .base import GenerationRequest, GenerationResult, Provider, ProviderNotConfigured


class ExternalProvider(Provider):
    name = "external"
    env_var = ""
    hint = ""

    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    @property
    def is_stub(self) -> bool:
        return True  # пока _call_api не реализован

    def _call_api(self, req: GenerationRequest) -> tuple[bytes, str, str, float]:
        raise ProviderNotConfigured(
            f"{self.name}: ЗАГЛУШКА — вызов реального API не реализован (метод _call_api в app/ai/external.py). {self.hint}"
        )

    def generate(self, req: GenerationRequest) -> GenerationResult:
        if not self.configured:
            raise ProviderNotConfigured(f"{self.name}: не задан ключ {self.env_var}. {self.hint}")
        data, ext, mime, cost = self._call_api(req)
        return GenerationResult(data, ext, mime, self.name, cost, False)


class ExternalImageProvider(ExternalProvider):
    name = "image-api"
    kind = "photo"
    env_var = "IMAGE_API_KEY"
    hint = "Выберите сервис генерации изображений, который принимает фото и промпт, и реализуйте вызов."


class ExternalVideoProvider(ExternalProvider):
    name = "video-api"
    kind = "video"
    env_var = "VIDEO_API_KEY"
    hint = "Выберите сервис генерации видео из изображения и реализуйте вызов (обычно асинхронная задача)."


class SeedanceVideoProvider(ExternalProvider):
    name = "seedance-2.5"
    kind = "video"
    env_var = "SEEDANCE_API_KEY"
    hint = (
        "Премиальные видео: подключайте, только если у Seedance 2.5 есть реальный доступный API "
        "(наличие и условия не проверены). Если API нет — смените модель шаблона на video-default в админке."
    )
