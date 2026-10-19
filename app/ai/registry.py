"""Маршрутизатор моделей: выбор провайдера по типу генерации и ключу модели.

Схема: интерфейс → API → сервис генерации → маршрутизатор (этот модуль) → провайдер.
В демо-режиме (AI_MODE=mock) любая модель обслуживается демо-провайдером своего типа. В боевом (AI_MODE=live) ключ
модели (provider_key) ищется среди настоящих провайдеров из external.py; пока их вызов не написан, генерация честно
завершается ошибкой «не подключено» и токены возвращаются."""
from __future__ import annotations

from .base import GenerationRequest, Provider, ProviderError, ProviderNotConfigured
from .external import ExternalAudioProvider, ExternalImageProvider, ExternalVideoProvider, SeedanceVideoProvider
from .mock import MockAudioProvider, MockImageProvider, MockVideoProvider


class ProviderRegistry:
    def __init__(self, mode: str = "mock", image_key: str = "", video_key: str = "", seedance_key: str = "", audio_key: str = "",
                 demo_delay: float = 0.0):
        self.mode = mode
        self._mock = {"photo": MockImageProvider(demo_delay), "video": MockVideoProvider(demo_delay), "audio": MockAudioProvider(demo_delay)}
        self._live: dict[str, Provider] = {
            "image-default": ExternalImageProvider(image_key),
            "video-default": ExternalVideoProvider(video_key),
            "audio-default": ExternalAudioProvider(audio_key),
            "seedance-2.5": SeedanceVideoProvider(seedance_key),
        }

    def get(self, kind: str, model: str) -> Provider:
        if self.mode == "mock":
            return self._mock[kind]
        provider = self._live.get(model)
        if provider is None:
            raise ProviderNotConfigured(f"Неизвестная модель «{model}»")
        if provider.kind != kind:
            raise ProviderError(f"Модель «{model}» не подходит для типа «{kind}»")
        return provider

    def describe(self) -> list[dict]:
        if self.mode == "mock":
            return [
                {"model": "(любая)", "kind": k, "provider": p.name, "configured": True, "stub": True}
                for k, p in self._mock.items()
            ]
        return [
            {"model": m, "kind": p.kind, "provider": p.name, "configured": p.configured, "stub": p.is_stub}
            for m, p in self._live.items()
        ]


__all__ = ["ProviderRegistry", "GenerationRequest"]
