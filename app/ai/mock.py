"""ДЕМО-РЕЖИМ (AI_MODE=mock): это НЕ настоящая генерация.

Картинки рисуются локально в оттенках серого (если есть ваше фото — оно обрабатывается: ч/б, контраст) и всегда
подписаны «ДЕМО · НЕ НАСТОЯЩАЯ ГЕНЕРАЦИЯ». Видео — короткая GIF-анимация, аудио — простая мелодия-заглушка (не речь).
Раскадровка, 9 ракурсов и примерка тоже демонстрационные. Нужно это, чтобы пройти весь путь
«запрос → заказ → результат → следующий шаг» без ключей и без расходов.
"""
from __future__ import annotations

import hashlib
import io
import math
import random
import struct
import time
import wave
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

from .base import GenerationRequest, GenerationResult, Provider

BANNER = "ДЕМО · НЕ НАСТОЯЩАЯ ГЕНЕРАЦИЯ"
SIZES = {"1:1": (768, 768), "3:4": (672, 896), "4:3": (896, 672), "9:16": (576, 1024), "16:9": (1024, 576), "21:9": (1008, 432)}
FONT_PATH = Path(__file__).parent / "fonts" / "DejaVuSans-Bold.ttf"

STORYBOARD = ["Общий план", "Дальний план", "Средний план", "Крупный план", "Деталь", "Через плечо", "Нижний ракурс", "Верхний ракурс", "Финальный кадр"]
ANGLES = ["Спереди", "Слева", "Справа", "Три четверти слева", "Три четверти справа", "Сзади", "Снизу", "Сверху", "Кинематографический"]


def _font(size: int):
    try:
        return ImageFont.truetype(str(FONT_PATH), size)
    except OSError:
        try:
            return ImageFont.load_default(size=size)
        except TypeError:  # старые версии Pillow
            return ImageFont.load_default()


def seed_of(req: GenerationRequest, salt: str = "") -> int:
    explicit = req.params.get("seed")
    key = f"{req.prompt}|{req.title}|{explicit if explicit not in (None, '') else req.order_id}|{salt}"
    return int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:12], 16)


def _banner(im: Image.Image, text: str = BANNER) -> Image.Image:
    im = im.convert("RGB")
    w, h = im.size
    draw = ImageDraw.Draw(im, "RGBA")
    size = max(13, min(w // 24, 30))
    bar = int(size * 2.1)
    draw.rectangle([0, h - bar, w, h], fill=(0, 0, 0, 235))
    draw.text((w // 2, h - bar // 2), text, fill=(255, 255, 255), font=_font(size), anchor="mm")
    return im


def _label(im: Image.Image, text: str) -> Image.Image:
    draw = ImageDraw.Draw(im, "RGBA")
    w, h = im.size
    size = max(12, w // 22)
    f = _font(size)
    box = draw.textbbox((0, 0), text, font=f)
    tw, th = box[2] - box[0], box[3] - box[1]
    draw.rectangle([10, 10, 10 + tw + 18, 10 + th + 14], fill=(0, 0, 0, 220))
    draw.text((19, 16), text, fill=(255, 255, 255), font=f)
    return im


def _art(size: tuple[int, int], seed: int) -> Image.Image:
    """Абстрактная чёрно-белая картинка: градиент, мягкие круги, линии, зерно. Для каждого запроса — своя."""
    rnd = random.Random(seed)
    w, h = size
    grad = Image.linear_gradient("L").resize((w, h))
    if rnd.random() < 0.5:
        grad = ImageOps.flip(grad)
    if rnd.random() < 0.5:
        grad = grad.rotate(90, expand=True).resize((w, h))
    lo, hi = rnd.randint(0, 25), rnd.randint(110, 190)
    im = ImageOps.colorize(grad, black=(lo,) * 3, white=(hi,) * 3).convert("RGB")
    layer = Image.new("RGB", size, (0, 0, 0))
    d = ImageDraw.Draw(layer)
    for _ in range(rnd.randint(4, 8)):
        r = rnd.randint(min(w, h) // 8, min(w, h) // 2)
        x, y = rnd.randint(0, w), rnd.randint(0, h)
        v = rnd.randint(30, 255)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(v, v, v))
    layer = layer.filter(ImageFilter.GaussianBlur(max(w, h) // 14))
    im = ImageChops.screen(im, ImageEnhance.Brightness(layer).enhance(0.55))
    d = ImageDraw.Draw(im, "RGBA")
    for _ in range(rnd.randint(2, 5)):
        x0, y0 = rnd.randint(0, w), rnd.randint(0, h)
        x1, y1 = x0 + rnd.randint(-w, w), y0 + rnd.randint(-h, h)
        v = rnd.choice([0, 255])
        d.line([x0, y0, x1, y1], fill=(v, v, v, 90), width=rnd.randint(1, 4))
    noise = Image.effect_noise(size, 18).convert("RGB")
    return Image.blend(im, noise, 0.07)


def _gray_photo(data: bytes, size: tuple[int, int]) -> Image.Image:
    with Image.open(io.BytesIO(data)) as im:
        im = ImageOps.fit(im.convert("RGB"), size)
    return ImageOps.autocontrast(ImageOps.grayscale(im), cutoff=1).convert("RGB")


def _size(req: GenerationRequest) -> tuple[int, int]:
    return SIZES.get(req.params.get("format", ""), (768, 768))


def _base(req: GenerationRequest, size: tuple[int, int] | None = None, salt: str = "") -> Image.Image:
    size = size or _size(req)
    if req.image:
        return _gray_photo(req.image, size)
    return _art(size, seed_of(req, salt))


def _stage(req: GenerationRequest, name: str, delay: float) -> None:
    if req.progress:
        req.progress(name)
    if delay > 0:
        time.sleep(delay)


class MockImageProvider(Provider):
    name = "mock-image"
    kind = "photo"

    def __init__(self, delay: float = 0.0):
        self.delay = delay

    @property
    def is_stub(self) -> bool:
        return True

    def generate(self, req: GenerationRequest) -> GenerationResult:
        _stage(req, "creating", self.delay)
        tool = req.tool
        if tool == "storyboard":
            frames, sheet = self._storyboard(req)
        elif tool == "angles":
            frames, sheet = self._angles(req)
        else:
            frames, sheet = (), None
        _stage(req, "processing", self.delay)
        if sheet is None:
            im = self._tryon(req) if tool == "tryon" and req.image else _base(req)
            if req.params.get("resolution") in ("2k", "4k"):
                im = im.resize((im.width * 3 // 2, im.height * 3 // 2), Image.LANCZOS)
            sheet = im
        _stage(req, "almost", self.delay / 2)
        out = io.BytesIO()
        _banner(sheet).save(out, "JPEG", quality=88)
        return GenerationResult(out.getvalue(), "jpg", "image/jpeg", self.name, 0.0, True, frames=frames)

    def redo_frame(self, data: bytes, label: str, seed: int) -> bytes:
        """Перегенерация одного кадра (демо): другой кадр/наклон/яркость того же изображения."""
        rnd = random.Random(seed)
        with Image.open(io.BytesIO(data)) as im:
            im = im.convert("RGB")
        w, h = im.size
        z = rnd.uniform(1.05, 1.35)
        cw, ch = int(w / z), int(h / z)
        x0, y0 = rnd.randint(0, w - cw), rnd.randint(0, h - ch)
        im = im.crop((x0, y0, x0 + cw, y0 + ch)).resize((w, h), Image.LANCZOS)
        if rnd.random() < 0.5:
            im = ImageOps.mirror(im)
        im = ImageEnhance.Contrast(im).enhance(rnd.uniform(0.9, 1.3))
        out = io.BytesIO()
        _banner(_label(im, label)).save(out, "JPEG", quality=86)
        return out.getvalue()

    # --- особые инструменты ---
    def _tryon(self, req: GenerationRequest) -> Image.Image:
        im = _base(req)
        if req.image2:
            g = _gray_photo(req.image2, (im.width // 3, im.width // 3))
            g = ImageOps.expand(g, border=4, fill=(255, 255, 255))
            im.paste(g, (im.width - g.width - 18, 18))
            _label(im, "Примерка (демо)")
        return im

    def _shot(self, base: Image.Image, spec: str, i: int, size: tuple[int, int]) -> Image.Image:
        w, h = size
        src = ImageOps.fit(base, size)
        zoom = {"Общий план": 1.0, "Дальний план": 0.55, "Средний план": 1.25, "Крупный план": 1.9, "Деталь": 3.0, "Через плечо": 1.4,
                "Нижний ракурс": 1.3, "Верхний ракурс": 1.3, "Финальный кадр": 1.15}.get(spec, 1.0)
        if zoom < 1:
            canvas = Image.new("RGB", size, (24, 24, 24))
            small = src.resize((int(w * zoom), int(h * zoom)))
            canvas.paste(small, ((w - small.width) // 2, (h - small.height) // 2))
            return canvas
        cw, ch = int(w / zoom), int(h / zoom)
        ax = {"Через плечо": 0.7}.get(spec, 0.5)
        ay = {"Нижний ракурс": 0.75, "Верхний ракурс": 0.25, "Крупный план": 0.35, "Деталь": 0.45}.get(spec, 0.5)
        x0, y0 = int((w - cw) * ax), int((h - ch) * ay)
        im = src.crop((x0, y0, x0 + cw, y0 + ch)).resize(size, Image.LANCZOS)
        if spec == "Через плечо":
            d = ImageDraw.Draw(im, "RGBA")
            d.polygon([(0, h), (0, int(h * 0.45)), (int(w * 0.28), int(h * 0.62)), (int(w * 0.34), h)], fill=(0, 0, 0, 215))
        if spec == "Финальный кадр":
            vg = Image.radial_gradient("L").resize(size)
            im = ImageChops.multiply(im, ImageOps.invert(vg).point(lambda v: 255 - int(v * 0.5)).convert("RGB"))
        if spec in ("Нижний ракурс", "Верхний ракурс"):
            im = im.rotate(-4 if spec == "Нижний ракурс" else 4, resample=Image.BICUBIC)
        return im

    def _storyboard(self, req: GenerationRequest):
        size = (512, 288)
        frames = []
        for i, spec in enumerate(STORYBOARD, 1):
            base = _base(req, (1024, 576), salt="" if req.image else f"sb{i}")
            if not req.image:  # без фото — у каждого кадра своя картинка
                im = ImageOps.fit(base, size)
                if spec in ("Крупный план", "Деталь"):
                    im = self._shot(base, spec, i, size)
            else:
                im = self._shot(base, spec, i, size)
            im = _label(im, f"{i} · {spec}")
            out = io.BytesIO()
            _banner(im).save(out, "JPEG", quality=86)
            frames.append((f"{i} · {spec}", out.getvalue()))
        return tuple(frames), make_sheet(frames, 3, size)

    def _angles(self, req: GenerationRequest):
        size = (384, 480)
        frames = []
        for i, spec in enumerate(ANGLES, 1):
            base = _base(req, size, salt="" if req.image else f"an{i}")
            im = base
            if spec in ("Слева", "Справа", "Три четверти слева", "Три четверти справа"):
                k = {"Слева": -0.22, "Справа": 0.22, "Три четверти слева": -0.1, "Три четверти справа": 0.1}[spec]
                im = base.transform(size, Image.AFFINE, (1, k, -k * size[1] / 2 if k > 0 else -k * size[1] / 2, 0, 1, 0), resample=Image.BICUBIC, fillcolor=(24, 24, 24))
            elif spec == "Сзади":
                im = ImageOps.mirror(base).filter(ImageFilter.GaussianBlur(5))
            elif spec == "Снизу":
                im = base.crop((0, 60, size[0], size[1])).resize(size, Image.LANCZOS)
            elif spec == "Сверху":
                im = base.crop((0, 0, size[0], size[1] - 60)).resize(size, Image.LANCZOS)
            elif spec == "Кинематографический":
                im = ImageEnhance.Contrast(base).enhance(1.4)
                d = ImageDraw.Draw(im)
                d.rectangle([0, 0, size[0], 44], fill=(0, 0, 0))
                d.rectangle([0, size[1] - 44, size[0], size[1]], fill=(0, 0, 0))
            im = _label(im.copy(), f"{i} · {spec}")
            out = io.BytesIO()
            _banner(im).save(out, "JPEG", quality=86)
            frames.append((f"{i} · {spec}", out.getvalue()))
        return tuple(frames), make_sheet(frames, 3, size)


def make_sheet(frames, cols: int, cell: tuple[int, int]) -> Image.Image:
    rows = math.ceil(len(frames) / cols)
    gap = 6
    sheet = Image.new("RGB", (cols * cell[0] + (cols + 1) * gap, rows * cell[1] + (rows + 1) * gap), (255, 255, 255))
    for n, (_, data) in enumerate(frames):
        with Image.open(io.BytesIO(data)) as im:
            im = ImageOps.fit(im.convert("RGB"), cell)
        r, c = divmod(n, cols)
        sheet.paste(im, (gap + c * (cell[0] + gap), gap + r * (cell[1] + gap)))
    return sheet


class MockVideoProvider(Provider):
    name = "mock-video"
    kind = "video"

    def __init__(self, delay: float = 0.0):
        self.delay = delay

    @property
    def is_stub(self) -> bool:
        return True

    def generate(self, req: GenerationRequest) -> GenerationResult:
        _stage(req, "creating", self.delay)
        base = _base(req)
        base.thumbnail((384, 384))
        base = base.convert("RGB")
        _stage(req, "processing", self.delay)
        frames = []
        n = 12
        for i in range(n):
            t = i / (n - 1)
            z = 1.0 + 0.08 * math.sin(math.pi * t)  # плавное приближение и возврат
            w, h = base.size
            cw, ch = int(w / z), int(h / z)
            fr = base.crop(((w - cw) // 2, (h - ch) // 2, (w - cw) // 2 + cw, (h - ch) // 2 + ch)).resize((w, h), Image.LANCZOS)
            frames.append(_banner(ImageEnhance.Brightness(fr).enhance(0.85 + 0.15 * math.sin(math.pi * t))).convert("P", palette=Image.ADAPTIVE))
        _stage(req, "almost", self.delay / 2)
        out = io.BytesIO()
        frames[0].save(out, "GIF", save_all=True, append_images=frames[1:], duration=250, loop=0)
        return GenerationResult(out.getvalue(), "gif", "image/gif", self.name, 0.0, True, round(n * 250 / 1000))


# ---------------------------------------------------------------- аудио

VOICE_BASE = {"alina": 262.0, "maxim": 147.0, "olga": 233.0, "igor": 110.0, "sofia": 294.0}
SCALE = [0, 2, 4, 7, 9, 12]  # пентатоника — мелодия звучит ровно


def synth_demo_audio(text: str, params: dict, rate: int = 16000) -> tuple[bytes, int]:
    """Мелодия-заглушка: по одной ноте на слово. Это НЕ синтез речи — только проверка пути «текст → аудиофайл»."""
    words = text.split() or ["…"]
    speed = float(params.get("speed") or 1.0)
    speed = min(max(speed, 0.5), 2.0)
    base = VOICE_BASE.get(params.get("voice") or "", 196.0)
    emotion = params.get("emotion") or "neutral"
    bright = {"joy": 1.0, "inspire": 0.9, "solemn": -0.5, "sad": -1.0, "calm": -0.2}.get(emotion, 0.0)
    samples: list[int] = []
    max_words = 90
    for w in words[:max_words]:
        h = int(hashlib.md5(w.encode("utf-8")).hexdigest()[:4], 16)
        step = SCALE[h % len(SCALE)]
        freq = base * 2 ** ((step + bright * 2) / 12)
        dur = min(0.55, 0.16 + 0.03 * len(w)) / speed
        n = int(rate * dur)
        vib = 3 if emotion in ("joy", "inspire") else 0
        for i in range(n):
            t = i / rate
            env = min(1.0, i / (rate * 0.02)) * min(1.0, (n - i) / (rate * 0.05))
            s = math.sin(2 * math.pi * (freq + vib * math.sin(2 * math.pi * 5 * t)) * t) * 0.35
            samples.append(int(s * env * 32767))
        samples.extend([0] * int(rate * 0.04 / speed))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(struct.pack("<%dh" % len(samples), *samples))
    return buf.getvalue(), max(1, round(len(samples) / rate))


class MockAudioProvider(Provider):
    name = "mock-audio"
    kind = "audio"

    def __init__(self, delay: float = 0.0):
        self.delay = delay

    @property
    def is_stub(self) -> bool:
        return True

    def generate(self, req: GenerationRequest) -> GenerationResult:
        _stage(req, "creating", self.delay)
        data, seconds = synth_demo_audio(req.prompt, req.params)
        _stage(req, "almost", self.delay / 2)
        return GenerationResult(data, "wav", "audio/wav", self.name, 0.0, True, seconds)
