"""ТЕСТОВЫЙ РЕЖИМ (AI_MODE=mock): это НЕ настоящая генерация.

Если фото есть, оно слегка обрабатывается локально; если фото нет — рисуется тёмный градиент.
Поверх всегда заметная надпись «TEST MODE». Видео — короткая GIF-анимация. Нужны только чтобы
проверить весь путь «запрос → заказ → результат» без ключей и без расходов.
"""
from __future__ import annotations

import io

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

from .base import GenerationRequest, GenerationResult, Provider

BANNER = "TEST MODE - NOT A REAL AI RESULT"
SIZES = {"1:1": (768, 768), "3:4": (672, 896), "4:3": (896, 672), "9:16": (576, 1024), "16:9": (1024, 576)}


def _banner(im: Image.Image) -> Image.Image:
    im = im.convert("RGB")
    w, h = im.size
    draw = ImageDraw.Draw(im, "RGBA")
    size = max(14, w // 22)
    try:
        font = ImageFont.load_default(size=size)
    except TypeError:  # старые версии Pillow
        font = ImageFont.load_default()
    bar = size * 2
    draw.rectangle([0, h - bar, w, h], fill=(21, 22, 23, 235))
    draw.text((w // 2, h - bar // 2), BANNER, fill=(229, 211, 176), font=font, anchor="mm")
    return im


def _canvas(size: tuple[int, int]) -> Image.Image:
    """Тёмный градиент (графит → тёплый champagne) для генерации без фото."""
    w, h = size
    im = Image.new("RGB", size)
    px = im.load()
    top, bottom = (21, 22, 23), (96, 84, 62)
    for y in range(h):
        t = y / h
        row = tuple(int(top[k] * (1 - t) + bottom[k] * t) for k in range(3))
        for x in range(w):
            px[x, y] = row
    d = ImageDraw.Draw(im, "RGBA")
    cx, cy, r = w // 2, h // 2, min(w, h) // 5
    d.polygon([(cx, cy - r), (cx + r // 4, cy - r // 4), (cx + r, cy), (cx + r // 4, cy + r // 4),
               (cx, cy + r), (cx - r // 4, cy + r // 4), (cx - r, cy), (cx - r // 4, cy - r // 4)], fill=(229, 211, 176, 200))
    return im


def _base(req: GenerationRequest) -> Image.Image:
    size = SIZES.get(req.params.get("format", ""), (768, 768))
    if not req.image:
        return _canvas(size)
    with Image.open(io.BytesIO(req.image)) as im:
        return ImageOps.posterize(ImageOps.fit(im.convert("RGB"), size), 4)


class MockImageProvider(Provider):
    name = "mock-image"
    kind = "photo"

    @property
    def is_stub(self) -> bool:
        return True

    def generate(self, req: GenerationRequest) -> GenerationResult:
        out = io.BytesIO()
        _banner(_base(req)).save(out, "JPEG", quality=88)
        return GenerationResult(out.getvalue(), "jpg", "image/jpeg", self.name, 0.0, True)


class MockVideoProvider(Provider):
    name = "mock-video"
    kind = "video"

    @property
    def is_stub(self) -> bool:
        return True

    def generate(self, req: GenerationRequest) -> GenerationResult:
        base = _base(req)
        base.thumbnail((384, 384))
        frames = []
        for i in range(8):
            factor = 0.75 + 0.25 * abs(4 - i) / 4
            frames.append(_banner(ImageEnhance.Brightness(base).enhance(factor)).convert("P", palette=Image.ADAPTIVE))
        out = io.BytesIO()
        frames[0].save(out, "GIF", save_all=True, append_images=frames[1:], duration=160, loop=0)
        seconds = max(1, round(len(frames) * 160 / 1000))
        return GenerationResult(out.getvalue(), "gif", "image/gif", self.name, 0.0, True, seconds)
