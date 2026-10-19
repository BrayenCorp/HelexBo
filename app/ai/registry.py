"""Выбор провайдера по типу и модели шаблона."""
from __future__ import annotations

from .base import GenerationRequest, Provider, ProviderError, ProviderNotConfigured
from .external import ExternalImageProvider, ExternalVideoProvider, SeedanceVideoProvider
from .mock import MockImageProvider, MockVideoProvider


class ProviderRegistry:
    def __init__(self, mode: str = "mock", image_key: str = "", video_key: str = "", seedance_key: str = ""):
        self.mode = mode
        self._mock = {"photo": MockImageProvider(), "video": MockVideoProvider()}
        self._live: dict[str, Provider] = {
            "image-default": ExternalImageProvider(image_key),
            "video-default": ExternalVideoProvider(video_key),
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
