"""Создание контента прямо в боте: фото, видео и аудио.

Бот — такой же интерфейс Nolla AI, как и приложение: те же сервисы, та же база, тот же баланс
и та же история. Здесь только диалог (кнопки и короткие шаги) — вся логика в app/services.

Три сценария:
  фото  — описание → модель → стоимость → создание
  видео — фото или описание → модель → стоимость → создание
  аудио — текст → голос → интонация → стоимость → создание

Плюс обычные сообщения: «создай фото…», «оживи это фото», «озвучь текст» — бот сам понимает,
что нужно сделать, и подставляет последнюю работу, когда человек говорит «его», «это фото».
"""
from __future__ import annotations

import asyncio
import io
import logging

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .context import AppContext
from .errors import DomainError, InsufficientCredits
from .services import models as models_service, orders

log = logging.getLogger(__name__)

KIND_WORD = {"photo": "изображение", "video": "видео", "audio": "аудио"}
KIND_EMOJI = {"photo": "📷", "video": "🎬", "audio": "🎙"}
VOICES = [("alina", "👩 Алина — мягкий"), ("olga", "👩 Ольга — дикторский"), ("sofia", "👩 Софья — молодой"),
          ("maxim", "👨 Максим — спокойный"), ("igor", "👨 Игорь — глубокий")]
TONES = [("even", "Ровная"), ("ad", "Рекламная"), ("confidential", "Доверительная"), ("exclaim", "Восклицательная"), ("question", "Вопросительная")]
EMOTIONS = {"even": "neutral", "ad": "inspire", "confidential": "calm", "exclaim": "joy", "question": "neutral"}


class Make(StatesGroup):
    prompt = State()      # ждём описание (фото/видео)
    text = State()        # ждём текст для озвучки
    picking = State()     # выбор модели/голоса/интонации — ответы приходят кнопками


# ---------------------------------------------------------------- понимание обычных сообщений
AUDIO_WORDS = ("озвуч", "озвучк", "проговори", "прочитай вслух", "голосом", "аудио", "дикто", "подкаст")
VIDEO_WORDS = ("видео", "оживи", "ожив", "анимируй", "анимац", "ролик", "клип", "сделай движение", "в движении")
PHOTO_WORDS = ("фото", "изображен", "картин", "нарисуй", "портрет", "снимок", "обложк", "аватар")
REF_WORDS = ("это фото", "этого фото", "эту фотограф", "этой фотограф", "из него", "из неё", "из этого", "его", "её", "последн", "предыдущ")
TOOL_WORDS = (
    ("раскадров", "fx-storyboard"), ("9 ракурс", "fx-angles"), ("девять ракурс", "fx-angles"), ("ракурс", "fx-angles"),
    ("примерь", "fx-tryon"), ("примерк", "fx-tryon"), ("замени фон", "fx-bg"), ("фон на", "fx-bg"),
    ("кинематограф", "fx-cinema"), ("улучши", "fx-enhance"), ("восстанов", "fx-restore"), ("кожу", "fx-skin"),
    ("фотосесси", "ps-luxury-studio"), ("товар", "mt-product-photo"), ("реклам", "mt-ad-image"),
)


def guess_kind(text: str) -> str:
    """Чего хочет человек: аудио, видео или изображение. По умолчанию — изображение."""
    t = (text or "").casefold()
    if any(w in t for w in AUDIO_WORDS):
        return "audio"
    if any(w in t for w in VIDEO_WORDS):
        return "video"
    if any(w in t for w in PHOTO_WORDS):
        return "photo"
    return "photo"


def guess_tool(text: str) -> str:
    t = (text or "").casefold()
    for word, slug in TOOL_WORDS:
        if word in t:
            return slug
    return ""


def wants_last_result(text: str) -> bool:
    t = (text or "").casefold()
    return any(w in t for w in REF_WORDS)


def last_image_order(ctx: AppContext, user_id: int) -> dict | None:
    """Последняя готовая картинка пользователя — её бот подставляет, когда говорят «это фото»."""
    with ctx.db.read() as c:
        row = c.execute(
            "SELECT id, prompt, model_id FROM orders WHERE user_id = ? AND kind = 'photo' AND status = 'done' "
            "AND result_mime LIKE 'image/jpeg%' AND is_hidden = 0 ORDER BY id DESC LIMIT 1", (user_id,)).fetchone()
    return dict(row) if row else None


# ---------------------------------------------------------------- клавиатуры и тексты
def cancel_row(kb: InlineKeyboardBuilder) -> None:
    kb.row(InlineKeyboardButton(text="✖️ Отмена", callback_data="menu:home"))


def models_kb(ctx: AppContext, kind: str, has_image: bool) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    for m in models_service.public_list(ctx.db, kind):
        if m["needs_image"] and not has_image:
            continue
        if m["text_only"] and has_image:
            continue
        kb.row(InlineKeyboardButton(text=f"{m['name']} · {m['price_credits']} ток.", callback_data=f"mk:model:{m['id']}"))
    cancel_row(kb)
    return kb


def price_line(ctx: AppContext, user_id: int, *, kind: str, model_id: int | None, template_id: int | None) -> str:
    try:
        q = orders.quote(ctx.db, user_id, template_id=template_id, kind=kind, model_id=model_id)
    except DomainError:
        return ""
    if q["free"]:
        return "💚 Стоимость: бесплатно — это ваша первая работа."
    return f"💎 Стоимость: {q['base']} токенов"


def confirm_kb() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="✨ Создать", callback_data="mk:go"))
    cancel_row(kb)
    return kb


def result_kb(order: dict) -> InlineKeyboardBuilder:
    """Кнопки под готовой работой — свои для фото, видео и аудио."""
    kb = InlineKeyboardBuilder()
    oid = order["id"]
    if order["kind"] == "photo":
        kb.row(InlineKeyboardButton(text="⬇️ Скачать", callback_data=f"res:dl:{oid}"),
               InlineKeyboardButton(text="🔁 Создать заново", callback_data=f"res:again:{oid}"))
        kb.row(InlineKeyboardButton(text="✏️ Изменить", callback_data=f"res:edit:{oid}"),
               InlineKeyboardButton(text="✨ Вариация", callback_data=f"res:var:{oid}"))
        kb.row(InlineKeyboardButton(text="🎬 Сделать видео", callback_data=f"res:video:{oid}"))
    elif order["kind"] == "video":
        kb.row(InlineKeyboardButton(text="▶️ Смотреть", callback_data=f"res:dl:{oid}"),
               InlineKeyboardButton(text="⬇️ Скачать", callback_data=f"res:dl:{oid}"))
        kb.row(InlineKeyboardButton(text="🔁 Создать заново", callback_data=f"res:again:{oid}"))
    else:
        kb.row(InlineKeyboardButton(text="▶️ Прослушать", callback_data=f"res:dl:{oid}"),
               InlineKeyboardButton(text="⬇️ Скачать", callback_data=f"res:dl:{oid}"))
        kb.row(InlineKeyboardButton(text="🔁 Создать заново", callback_data=f"res:again:{oid}"))
    return kb


# ---------------------------------------------------------------- запуск генерации
async def download(bot: Bot, file_id: str) -> bytes:
    buf = io.BytesIO()
    await bot.download(file_id, destination=buf)
    return buf.getvalue()


async def start_job(message: Message, state: FSMContext, ctx: AppContext, user_id: int, open_app) -> None:
    """Создаёт заказ из того, что человек собрал в диалоге. Источник — bot, поэтому работа
    сразу видна и в приложении, и в админке, а баланс общий."""
    data = await state.get_data()
    kind = data.get("kind", "photo")
    image = await download(message.bot, data["file_id"]) if data.get("file_id") else None
    gen_params = {}
    if kind == "audio":
        gen_params = {"voice": data.get("voice", "alina"), "tone": data.get("tone", "even"),
                      "emotion": EMOTIONS.get(data.get("tone", "even"), "neutral")}
    elif data.get("seed"):
        gen_params = {"seed": data["seed"]}
    try:
        order, created = await asyncio.to_thread(
            lambda: orders.submit_generation(
                ctx.db, ctx.storage, user_id=user_id, request_id=data.get("request_id") or f"bot:{message.chat.id}:{message.message_id}",
                source="bot", kind=None if data.get("template_id") else kind, template_id=data.get("template_id"),
                model_id=data.get("model_id"), prompt=data.get("prompt", ""), params=gen_params or None,
                image_bytes=image, ref_order_id=data.get("ref_order_id"), max_bytes=ctx.settings.max_upload_bytes,
            )
        )
    except InsufficientCredits:
        kb = InlineKeyboardBuilder()
        kb.row(open_app("💎 Пополнить в приложении"))
        await state.clear()
        return await message.answer("Не хватает токенов. Пополнить можно в приложении 👇", reply_markup=kb.as_markup())
    except DomainError as e:
        await state.clear()
        return await message.answer(f"⚠️ {e.message}")
    await state.clear()
    if not created:
        return
    waiting = {"photo": "🪄 Создаём изображение…", "video": "🎬 Подготавливаем видео…", "audio": "🎙 Записываем озвучку…"}[order["kind"]]
    await message.answer(f"{waiting}\nПришлю результат сюда, как только будет готово.")
    ctx.runner.schedule(order["id"])


async def ask_model(message: Message, state: FSMContext, ctx: AppContext) -> None:
    data = await state.get_data()
    kind = data.get("kind", "photo")
    await state.set_state(Make.picking)
    kb = models_kb(ctx, kind, bool(data.get("file_id") or data.get("ref_order_id")))
    await message.answer("🧠 <b>Выберите модель</b>", reply_markup=kb.as_markup())


async def ask_confirm(message: Message, state: FSMContext, ctx: AppContext, user_id: int) -> None:
    data = await state.get_data()
    kind = data.get("kind", "photo")
    model = None
    if data.get("model_id"):
        with ctx.db.read() as c:
            row = c.execute("SELECT name FROM ai_models WHERE id = ?", (data["model_id"],)).fetchone()
            model = row["name"] if row else None
    lines = [f"{KIND_EMOJI[kind]} <b>{KIND_WORD[kind].capitalize()}</b>"]
    if data.get("prompt"):
        lines.append(f"«{data['prompt'][:300]}»")
    if model:
        lines.append(f"🧠 Модель: {model}")
    if kind == "audio":
        voice = dict(VOICES).get(data.get("voice", "alina"), "")
        lines.append(f"🗣 Голос: {voice}")
        lines.append(f"🎵 Интонация: {dict(TONES).get(data.get('tone', 'even'), '')}")
    price = price_line(ctx, user_id, kind=kind, model_id=data.get("model_id"), template_id=data.get("template_id"))
    if price:
        lines.append(price)
    await state.set_state(Make.picking)
    await message.answer("\n".join(lines), reply_markup=confirm_kb().as_markup())
