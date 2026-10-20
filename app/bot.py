"""Telegram-бот Nolla AI на aiogram 3. Вся логика — в app/services, бот только показывает кнопки."""
from __future__ import annotations

import asyncio
import html
import io
import logging
from pathlib import Path

from aiogram import BaseMiddleware, Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BotCommand, CallbackQuery, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice,
    MenuButtonWebApp, Message, PreCheckoutQuery, WebAppInfo,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .context import AppContext
from .errors import DomainError, InsufficientCredits
from . import bot_create as bc
from .services import catalog, categories, credits, events, methods, orders, payments, templates, users

log = logging.getLogger(__name__)
router = Router()

STATUS_ICON = {"created": "…", "processing": "…", "done": "✓", "failed": "!"}


def esc(text: object) -> str:
    return html.escape(str(text))


BRAND = "Nolla AI"
BOT_DESCRIPTION = (
    "Nolla AI ✨ — студия для творчества в Telegram. Изображения и видео с лучшими AI-моделями: "
    "эффекты 🪄, тренды 🔥, фотосессии 📸 и реклама 📣. Опишите идею — остальное сделаем мы."
)
BOT_SHORT_DESCRIPTION = "✨ Изображения и видео с помощью AI. Опишите идею — и готово."

# Единственный источник приветствия. Другого текста в проекте нет: если в чате появился иной —
# значит, работает старая версия кода (чаще всего параллельно крутится прошлый деплой).
WELCOME_TEXT = (
    "<b>Добро пожаловать в Nolla AI.</b>\n\n"
    "Создавай изображения и видео с помощью современных AI-моделей."
)
MENU_TEXT = "Что создаём?"

# Метка сборки. Меняйте вместе с заметными правками бота: по ней видно, какой код сейчас отвечает.
BUILD = "2026-10-20.1"


# Эмодзи для разделов и категорий каталога — чтобы в чате было живо и понятно.
SECTION_EMOJI = {"effect": "🪄", "trend": "🔥", "photoshoot": "📸", "prompt": "✍️", "marketing": "📣", "mtool": "🛠", "avatar": "🧑‍🎤"}
SECTION_TITLE = {"effect": "Эффекты", "trend": "Тренды", "photoshoot": "Фотосессии", "prompt": "Промпты", "marketing": "Маркетинг", "avatar": "Аватары"}
TAG_EMOJI = {
    "women": "💃", "men": "🕺", "kids": "🧒", "family": "👨‍👩‍👧", "couples": "💞", "animals": "🐾", "birthday": "🎂",
    "fashion": "👗", "luxury": "💎", "lifestyle": "🌿", "business": "💼", "travel": "✈️", "editorial": "📰",
    "street": "🛹", "cinema": "🎬", "products": "📦", "ads": "📣", "social": "📱", "marketplaces": "🛒", "ugc": "🎥",
    "brands": "🏷", "architecture": "🏛", "marketing": "📣", "edit": "✏️", "photo": "🖼", "video": "🎞", "improve": "✨",
    "portrait": "🙂", "dance": "🕺",
}
PAGE_SIZE = 8


def card_emoji(t: dict) -> str:
    """Эмодзи карточки: по её категории, затем по разделу, затем общий значок."""
    return TAG_EMOJI.get(t.get("tag") or "") or SECTION_EMOJI.get(t.get("section") or "", "") or "✨"


def open_button(ctx: AppContext, text: str, slug: str = "") -> InlineKeyboardButton:
    """Кнопка, открывающая Mini App (при необходимости — сразу на нужной карточке)."""
    if ctx.settings.webapp_url:
        url = ctx.settings.webapp_url.rstrip("/") + (f"?slug={slug}" if slug else "")
        return InlineKeyboardButton(text=text, web_app=WebAppInfo(url=url))
    return InlineKeyboardButton(text=text, callback_data="menu:app")


def main_menu(ctx: AppContext) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="📷 Создать фото", callback_data="mk:new:photo"),
           InlineKeyboardButton(text="🎬 Создать видео", callback_data="mk:new:video"))
    kb.row(InlineKeyboardButton(text="💡 Посмотреть идеи", callback_data="mk:ideas:0"))
    kb.row(InlineKeyboardButton(text="🖼 Мои генерации", callback_data="menu:works"))
    kb.row(open_button(ctx, f"🚀 Открыть {BRAND}"))
    return kb.as_markup()


async def ensure_user(ctx: AppContext, tg_user) -> None:
    await asyncio.to_thread(users.upsert_user, ctx.db, tg_user.id, tg_user.username, tg_user.first_name)


class UserMiddleware(BaseMiddleware):
    """Каждое обновление: пользователь создаётся/обновляется, отмечается активность за день, вход через Telegram
    оформляется автоматически (нажатие «Старт» в боте — это и есть вход). Заблокированным бот не отвечает."""

    async def __call__(self, handler, event, data):
        ctx: AppContext = data["ctx"]
        user = getattr(event, "from_user", None)
        if user is None:
            return await handler(event, data)
        param = None
        text = getattr(event, "text", None) or ""
        if text.startswith("/start"):
            parts = text.split(maxsplit=1)
            param = parts[1].strip() if len(parts) > 1 else None
        u = await asyncio.to_thread(users.upsert_user, ctx.db, user.id, user.username, user.first_name, last_name=user.last_name,
                                    language_code=user.language_code, start_param=param)
        await asyncio.to_thread(users.register, ctx.db, user.id)
        if u["status"] == "blocked":
            msg = event.message if isinstance(event, CallbackQuery) else event
            if msg is not None:
                await msg.answer("Ваш аккаунт заблокирован. Обратитесь в поддержку.")
            if isinstance(event, CallbackQuery):
                await event.answer()
            return None
        return await handler(event, data)


def _log_command(ctx: AppContext, user_id: int, cmd: str) -> None:
    events.log(ctx.db, "bot_command", user_id, cmd=cmd)


# ---------- меню ----------
@router.message(CommandStart())
@router.message(Command("menu"))
async def cmd_start(message: Message, state: FSMContext, ctx: AppContext):
    await state.clear()
    await ensure_user(ctx, message.from_user)
    if (message.text or "").startswith("/start"):
        events.log(ctx.db, "bot_started", message.from_user.id)
    if not users.profile(ctx.db, message.from_user.id)["welcomed"]:
        users.mark_welcomed(ctx.db, message.from_user.id)
    await message.answer(WELCOME_TEXT, reply_markup=main_menu(ctx))


@router.callback_query(F.data == "menu:home")
async def cb_home(call: CallbackQuery, state: FSMContext, ctx: AppContext):
    await state.clear()
    await call.message.answer(MENU_TEXT, reply_markup=main_menu(ctx))
    await call.answer()


@router.callback_query(F.data == "menu:app")
async def cb_app_missing(call: CallbackQuery):
    await call.answer("Приложение ещё не подключено: администратору нужно задать WEBAPP_URL.", show_alert=True)


# ---------- баланс и оплата живут в приложении; обработчики оставлены для старых кнопок ----------
@router.callback_query(F.data == "menu:credits")
async def cb_credits(call: CallbackQuery, ctx: AppContext):
    await ensure_user(ctx, call.from_user)
    kb = InlineKeyboardBuilder()
    kb.row(open_button(ctx, "🎨 Открыть приложение"))
    kb.row(InlineKeyboardButton(text="🏠 В меню", callback_data="menu:home"))
    await call.message.answer("💼 Баланс, пополнение и история — в приложении.", reply_markup=kb.as_markup())
    await call.answer()


@router.callback_query(F.data.startswith("buy:"))
async def cb_buy(call: CallbackQuery, ctx: AppContext):
    avail = [m["code"] for m in methods.for_users(ctx.db, ctx.settings, True)["available"] if m["code"] in ("stars", "test")]
    if not avail:
        return await call.answer("Оплата пока недоступна. Загляните позже.", show_alert=True)
    method = "stars" if "stars" in avail else "test"
    try:
        pay = payments.create_payment(ctx.db, call.from_user.id, call.data.split(":")[1], method)
    except DomainError as e:
        return await call.answer(e.message, show_alert=True)
    total = pay["credits"] + pay["bonus"]
    if method == "test":
        payments.confirm_payment(ctx.db, pay["payload"], provider="test", user_id=call.from_user.id)
        bal = credits.get_balance(ctx.db, call.from_user.id)
        await call.message.answer(f"Тестовая оплата: начислено {total} ток. Баланс: {bal} ток.", reply_markup=main_menu(ctx))
    else:
        await call.message.answer_invoice(
            title=f"{total} токенов {BRAND}", description=f"Токены для создания фото и видео в {BRAND}",
            payload=pay["payload"], currency="XTR", provider_token="",
            prices=[LabeledPrice(label=f"{total} токенов", amount=pay["amount_stars"])],
        )
    await call.answer()


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery, ctx: AppContext):
    pay = payments.get_by_payload(ctx.db, query.invoice_payload)
    ok = bool(
        pay and pay["status"] == "pending" and pay["provider"] == "stars"
        and pay["user_id"] == query.from_user.id and query.total_amount == pay["amount_stars"]
        and query.currency == "XTR"
    )
    await query.answer(ok=ok, error_message=None if ok else "Платёж недействителен, попробуйте создать новый.")


@router.message(F.successful_payment)
async def successful_payment(message: Message, ctx: AppContext):
    sp = message.successful_payment
    try:
        pay, credited = payments.confirm_payment(
            ctx.db, sp.invoice_payload, provider="stars",
            provider_charge_id=sp.telegram_payment_charge_id, paid_stars=sp.total_amount, user_id=message.from_user.id,
        )
    except DomainError as e:
        # Деньги получены, а начислить не вышло — обязательно в лог для ручного разбора.
        log.error("Платёж %s не начислен: %s", sp.telegram_payment_charge_id, e.message)
        return await message.answer("Платёж получен, но токены не начислились автоматически. Мы разберёмся — напишите в поддержку.")
    bal = credits.get_balance(ctx.db, message.from_user.id)
    await message.answer(f"Оплата получена: +{pay['credits'] + pay['bonus']} ток. Баланс: {bal} ток." if credited else f"Платёж уже учтён. Баланс: {bal} ток.",
                         reply_markup=main_menu(ctx))


# ---------- мои работы ----------
@router.callback_query(F.data == "menu:works")
async def cb_works(call: CallbackQuery, ctx: AppContext):
    await ensure_user(ctx, call.from_user)
    items = orders.list_user_orders(ctx.db, call.from_user.id, 8)
    kb = InlineKeyboardBuilder()
    if not items:
        text = "🖼 Работ пока нет. Создайте первую — это весело! ✨"
    else:
        text = "🖼 <b>Мои работы</b>\nНажмите, чтобы получить файл ещё раз 👇"
        for o in items:
            kb.row(InlineKeyboardButton(text=f"{STATUS_ICON[o['status']]} {o['title']}", callback_data=f"work:{o['id']}"))
    kb.row(open_button(ctx, "🎨 Открыть приложение"))
    kb.row(InlineKeyboardButton(text="🏠 В меню", callback_data="menu:home"))
    await call.message.answer(text, reply_markup=kb.as_markup())
    await call.answer()


@router.callback_query(F.data.startswith("work:"))
async def cb_work(call: CallbackQuery, ctx: AppContext):
    o = orders.get_user_order(ctx.db, call.from_user.id, int(call.data.split(":")[1]))
    if o is None:
        return await call.answer("Работа не найдена", show_alert=True)
    if o["status"] in ("created", "processing"):
        return await call.answer("⏳ Ещё создаётся — результат придёт в чат.", show_alert=True)
    await BotNotifier(call.bot, ctx).notify_order(o)
    await call.answer()


# ---------- команды: /create /profile /history /settings ----------
@router.message(Command("create"))
async def cmd_create(message: Message, state: FSMContext, ctx: AppContext):
    await state.clear()
    _log_command(ctx, message.from_user.id, "create")
    await message.answer(MENU_TEXT, reply_markup=main_menu(ctx))


@router.message(Command("version"))
async def cmd_version(message: Message, ctx: AppContext):
    """Короткая проверка: какой код отвечает прямо сейчас."""
    _log_command(ctx, message.from_user.id, "version")
    await message.answer(
        f"🧩 <b>Сборка {BUILD}</b>\n"
        f"Приветствие: {esc(WELCOME_TEXT.splitlines()[0])}\n"
        f"Кнопок в меню: {sum(len(r) for r in main_menu(ctx).inline_keyboard)}\n\n"
        "Если здесь не та сборка, которую вы залили, — значит отвечает старый процесс бота."
    )


@router.message(Command("profile"))
async def cmd_profile(message: Message, ctx: AppContext):
    _log_command(ctx, message.from_user.id, "profile")
    done = orders.count_done_by_kind(ctx.db, message.from_user.id)
    name = esc(message.from_user.first_name or "")
    text = (f"👤 <b>Профиль</b>{': ' + name if name else ''}\n"
            f"🖼 Картинок: {done['photo']}\n🎞 Видео: {done['video']}\n\n"
            "Все подробности — в приложении ✨")
    kb = InlineKeyboardBuilder()
    kb.row(open_button(ctx, "🎨 Открыть приложение"))
    await message.answer(text, reply_markup=kb.as_markup())


@router.message(Command("history"))
async def cmd_history(message: Message, ctx: AppContext):
    _log_command(ctx, message.from_user.id, "history")
    items = orders.list_user_orders(ctx.db, message.from_user.id, 8)
    kb = InlineKeyboardBuilder()
    if not items:
        text = "🕘 Работ пока нет. Самое время создать первую! ✨"
    else:
        text = "🕘 <b>История</b>\nНажмите, чтобы получить файл ещё раз 👇"
        for o in items:
            kb.row(InlineKeyboardButton(text=f"{STATUS_ICON[o['status']]} {o['title']}", callback_data=f"work:{o['id']}"))
    await message.answer(text, reply_markup=kb.as_markup())


def _settings_kb(on: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=("🔔 Результаты в чат: включено" if on else "🔕 Результаты в чат: выключено"), callback_data=f"set:notify:{0 if on else 1}"))
    return kb.as_markup()


@router.message(Command("settings"))
async def cmd_settings(message: Message, ctx: AppContext):
    _log_command(ctx, message.from_user.id, "settings")
    on = users.profile(ctx.db, message.from_user.id)["notify_chat"]
    await message.answer("⚙️ <b>Настройки</b>\nПрисылать готовые работы в этот чат?", reply_markup=_settings_kb(on))


@router.callback_query(F.data.startswith("set:notify:"))
async def cb_set_notify(call: CallbackQuery, ctx: AppContext):
    on = call.data.endswith(":1")
    users.set_notify_chat(ctx.db, call.from_user.id, on)
    await call.message.edit_reply_markup(reply_markup=_settings_kb(on))
    await call.answer("Сохранено ✨")




# ======================  СОЗДАНИЕ ПРЯМО В БОТЕ  ======================
# Бот умеет то же, что приложение: фото, видео и аудио. Шаги короткие, всё на кнопках,
# а обычные сообщения бот понимает сам. Заказы идут через те же сервисы — общая база,
# общий баланс, общая история (см. app/bot_create.py).

def _open(ctx: AppContext):
    return lambda text, slug="": open_button(ctx, text, slug)


async def _ask_start(message: Message, state: FSMContext, ctx: AppContext, kind: str) -> None:
    await state.clear()
    await state.update_data(kind=kind)
    kb = InlineKeyboardBuilder()
    bc.cancel_row(kb)
    if kind == "audio":
        await state.set_state(bc.Make.text)
        await message.answer("🎙 <b>Создание аудио</b>\nВведите текст для озвучки (до 2000 символов).", reply_markup=kb.as_markup())
    elif kind == "video":
        await state.set_state(bc.Make.prompt)
        await message.answer("🎬 <b>Создание видео</b>\nОтправьте изображение или опишите сцену.", reply_markup=kb.as_markup())
    else:
        await state.set_state(bc.Make.prompt)
        await message.answer("📷 <b>Создание фото</b>\nОпишите, что хотите создать. Можно сразу прислать фото — тогда я его изменю.", reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("mk:new:"))
async def cb_make_new(call: CallbackQuery, state: FSMContext, ctx: AppContext):
    await ensure_user(ctx, call.from_user)
    kind = call.data.split(":")[2]
    if kind == "audio":  # раздел аудио выключен
        return await call.answer("Аудио пока не делаем.", show_alert=True)
    await _ask_start(call.message, state, ctx, kind)
    await call.answer()


@router.callback_query(F.data.startswith("mk:ideas"))
async def cb_ideas(call: CallbackQuery, ctx: AppContext):
    """Идеи — та же витрина, что и в приложении: её наполняет владелец в админке."""
    page = int(call.data.split(":")[2]) if len(call.data.split(":")) > 2 else 0
    items = catalog.list_items(ctx.db, "idea", on_ideas=True)
    if not items:  # витрина ещё пустая — показываем тренды и фотосессии
        items = catalog.list_items(ctx.db, "trend", limit=6) + catalog.list_items(ctx.db, "photoshoot", limit=6)
    kb = InlineKeyboardBuilder()
    for t in items[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]:
        kb.row(InlineKeyboardButton(text=f"{card_emoji(t)} {t['title']}", callback_data=f"mk:idea:{t['id']}"))
    nav = []
    if page:
        nav.append(InlineKeyboardButton(text="‹ Назад", callback_data=f"mk:ideas:{page - 1}"))
    if (page + 1) * PAGE_SIZE < len(items):
        nav.append(InlineKeyboardButton(text="Ещё ›", callback_data=f"mk:ideas:{page + 1}"))
    if nav:
        kb.row(*nav)
    kb.row(InlineKeyboardButton(text="✨ Все разделы", callback_data="menu:catalog"))
    kb.row(InlineKeyboardButton(text="🏠 В меню", callback_data="menu:home"))
    await call.message.answer("💡 <b>Идеи</b>\nВыберите — и попробуем прямо здесь 👇" if items else "💡 Идей пока нет.", reply_markup=kb.as_markup())
    await call.answer()


@router.callback_query(F.data.startswith("mk:idea:"))
async def cb_idea_try(call: CallbackQuery, state: FSMContext, ctx: AppContext):
    await ensure_user(ctx, call.from_user)
    try:
        t = catalog.get_item(ctx.db, int(call.data.split(":")[2]))
    except DomainError as e:
        return await call.answer(e.message, show_alert=True)
    await state.clear()
    await state.update_data(kind=t["kind"], template_id=t["id"], prompt="")
    needs = [r["code"] for r in t["required"]]
    if t["needs_avatar"]:
        kb = InlineKeyboardBuilder()
        kb.row(open_button(ctx, "🧑‍🎤 Создать аватар"))
        kb.row(InlineKeyboardButton(text="🏠 В меню", callback_data="menu:home"))
        await state.clear()
        await call.message.answer("🧑‍🎤 Для этой идеи нужен готовый аватар — его удобнее создать в приложении.", reply_markup=kb.as_markup())
        return await call.answer()
    if needs:
        last = bc.last_image_order(ctx, call.from_user.id)
        kb = InlineKeyboardBuilder()
        if last:
            kb.row(InlineKeyboardButton(text="🖼 Взять последнюю работу", callback_data=f"mk:uselast:{last['id']}"))
        bc.cancel_row(kb)
        await state.set_state(bc.Make.prompt)
        await call.message.answer(f"{card_emoji(t)} <b>{esc(t['title'])}</b>\n📷 Пришлите фото — и я всё сделаю.", reply_markup=kb.as_markup())
    else:
        await bc.ask_confirm(call.message, state, ctx, call.from_user.id)
    await call.answer()


@router.callback_query(F.data.startswith("mk:uselast:"))
async def cb_use_last(call: CallbackQuery, state: FSMContext, ctx: AppContext):
    await state.update_data(ref_order_id=int(call.data.split(":")[2]))
    data = await state.get_data()
    if data.get("template_id"):
        await bc.ask_confirm(call.message, state, ctx, call.from_user.id)
    else:
        await bc.ask_model(call.message, state, ctx)
    await call.answer()


@router.callback_query(F.data.startswith("mk:model:"))
async def cb_pick_model(call: CallbackQuery, state: FSMContext, ctx: AppContext):
    await state.update_data(model_id=int(call.data.split(":")[2]))
    await bc.ask_confirm(call.message, state, ctx, call.from_user.id)
    await call.answer()


@router.callback_query(F.data.startswith("mk:voice:"))
async def cb_pick_voice(call: CallbackQuery, state: FSMContext, ctx: AppContext):
    await state.update_data(voice=call.data.split(":")[2])
    kb = InlineKeyboardBuilder()
    for code, label in bc.TONES:
        kb.row(InlineKeyboardButton(text=label, callback_data=f"mk:tone:{code}"))
    bc.cancel_row(kb)
    await call.message.answer("🎵 <b>Выберите стиль озвучки</b>", reply_markup=kb.as_markup())
    await call.answer()


@router.callback_query(F.data.startswith("mk:tone:"))
async def cb_pick_tone(call: CallbackQuery, state: FSMContext, ctx: AppContext):
    await state.update_data(tone=call.data.split(":")[2])
    await bc.ask_confirm(call.message, state, ctx, call.from_user.id)
    await call.answer()


@router.callback_query(F.data.startswith("mk:withphoto:"))
async def cb_with_photo(call: CallbackQuery, state: FSMContext, ctx: AppContext):
    """Человек прислал фото без пояснений — выбирает, что с ним сделать."""
    what = call.data.split(":")[2]
    if what == "effects":
        await state.clear()
        kb = InlineKeyboardBuilder()
        kb.row(open_button(ctx, "🪄 Открыть эффекты"))
        kb.row(InlineKeyboardButton(text="🏠 В меню", callback_data="menu:home"))
        await call.message.answer("🪄 Эффекты, тренды и фотосессии — в приложении.", reply_markup=kb.as_markup())
        return await call.answer()
    await state.update_data(kind=what)
    if what == "photo":
        await state.set_state(bc.Make.prompt)
        kb = InlineKeyboardBuilder()
        bc.cancel_row(kb)
        await call.message.answer("✏️ Что изменить на фото? Опишите одним сообщением.", reply_markup=kb.as_markup())
    else:
        await bc.ask_model(call.message, state, ctx)
    await call.answer()


@router.callback_query(F.data == "mk:go")
async def cb_make_go(call: CallbackQuery, state: FSMContext, ctx: AppContext):
    await bc.start_job(call.message, state, ctx, call.from_user.id, _open(ctx))
    await call.answer()


# ---------- шаги мастера: тексты и фото ----------
@router.message(bc.Make.text, F.text)
async def make_audio_text(message: Message, state: FSMContext, ctx: AppContext):  # оставлено на случай, если аудио снова включат
    text = (message.text or "").strip()
    if len(text) > 2000:
        return await message.answer(f"Текст длиннее 2000 символов ({len(text)}). Сократите, пожалуйста 🙏")
    await state.update_data(prompt=text)
    kb = InlineKeyboardBuilder()
    for code, label in bc.VOICES:
        kb.row(InlineKeyboardButton(text=label, callback_data=f"mk:voice:{code}"))
    bc.cancel_row(kb)
    await message.answer("🗣 <b>Выберите голос</b>", reply_markup=kb.as_markup())


@router.message(bc.Make.prompt, F.photo)
async def make_got_photo(message: Message, state: FSMContext, ctx: AppContext):
    await state.update_data(file_id=message.photo[-1].file_id)
    if message.caption:
        await state.update_data(prompt=message.caption.strip()[:500])
    data = await state.get_data()
    if data.get("template_id"):
        await bc.ask_confirm(message, state, ctx, message.from_user.id)
    else:
        await bc.ask_model(message, state, ctx)


@router.message(bc.Make.prompt, F.text)
async def make_got_prompt(message: Message, state: FSMContext, ctx: AppContext):
    text = (message.text or "").strip()
    if len(text) > 500:
        return await message.answer(f"Описание длиннее 500 символов ({len(text)}). Сократите, пожалуйста 🙏")
    await state.update_data(prompt=text)
    data = await state.get_data()
    if data.get("template_id"):
        await bc.ask_confirm(message, state, ctx, message.from_user.id)
    else:
        await bc.ask_model(message, state, ctx)


@router.message(bc.Make.prompt)
@router.message(bc.Make.text)
async def make_other(message: Message):
    await message.answer("✍️ Пришлите текст или фото. Для отмены нажмите «Отмена» выше.")


# ---------- кнопки под готовой работой ----------
@router.callback_query(F.data.startswith("res:"))
async def cb_result_action(call: CallbackQuery, state: FSMContext, ctx: AppContext):
    _, what, raw = call.data.split(":")
    order = orders.get_user_order(ctx.db, call.from_user.id, int(raw))
    if order is None:
        return await call.answer("Работа не найдена", show_alert=True)
    if what == "dl":
        await BotNotifier(call.bot, ctx).notify_order(order, with_menu=False, with_actions=False)
        return await call.answer()
    await state.clear()
    base = {"kind": order["kind"], "prompt": order["prompt"] or "", "model_id": order["model_id"],
            "template_id": None if order["is_system"] else order["template_id"]}
    if what == "again":
        await state.update_data(**base)
        await bc.ask_confirm(call.message, state, ctx, call.from_user.id)
    elif what == "var":
        import random
        await state.update_data(**base, seed=random.randint(1, 2**31 - 2))
        await bc.ask_confirm(call.message, state, ctx, call.from_user.id)
    elif what == "edit":
        await state.update_data(kind="photo", ref_order_id=order["id"], model_id=order["model_id"])
        await state.set_state(bc.Make.prompt)
        kb = InlineKeyboardBuilder()
        bc.cancel_row(kb)
        await call.message.answer("✏️ Что изменить? Опишите одним сообщением.", reply_markup=kb.as_markup())
    elif what == "video":
        await state.update_data(kind="video", ref_order_id=order["id"], prompt=order["prompt"] or "")
        await bc.ask_model(call.message, state, ctx)
    await call.answer()


# ---------- обычные сообщения: бот понимает, что нужно сделать ----------
@router.message(F.photo)
async def free_photo_message(message: Message, state: FSMContext, ctx: AppContext):
    """Фото без мастера: с подписью — сразу в работу, без подписи — спрашиваем, что сделать."""
    await ensure_user(ctx, message.from_user)
    await state.clear()
    caption = (message.caption or "").strip()
    await state.update_data(file_id=message.photo[-1].file_id)
    if caption:
        kind = bc.guess_kind(caption)
        slug = bc.guess_tool(caption)
        await state.update_data(kind=kind, prompt=caption[:500])
        if slug:
            try:
                t = catalog.get_by_slug(ctx.db, slug)
                await state.update_data(template_id=t["id"], kind=t["kind"])
                return await bc.ask_confirm(message, state, ctx, message.from_user.id)
            except DomainError:
                pass
        return await bc.ask_model(message, state, ctx)
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="✏️ Изменить фото", callback_data="mk:withphoto:photo"))
    kb.row(InlineKeyboardButton(text="🎬 Сделать видео", callback_data="mk:withphoto:video"))
    kb.row(InlineKeyboardButton(text="🪄 Применить эффект", callback_data="mk:withphoto:effects"))
    bc.cancel_row(kb)
    await message.answer("📷 Красивое фото! Что с ним сделать?", reply_markup=kb.as_markup())


@router.message(F.text & ~F.text.startswith("/"))
async def free_text_message(message: Message, state: FSMContext, ctx: AppContext):
    """«Создай фото…», «оживи это фото», «озвучь текст» — бот сам понимает задачу и контекст."""
    await ensure_user(ctx, message.from_user)
    text = (message.text or "").strip()
    await state.clear()
    kind = bc.guess_kind(text)
    slug = bc.guess_tool(text)
    last = bc.last_image_order(ctx, message.from_user.id)

    if kind == "audio":  # раздел аудио выключен
        await state.clear()
        return await message.answer("Озвучку пока не делаем. Зато умеем изображения и видео 👇", reply_markup=main_menu(ctx))

    use_last = bool(last) and (bc.wants_last_result(text) or (slug and kind != "video"))
    await state.update_data(kind=kind, prompt=text[:500], **({"ref_order_id": last["id"]} if use_last else {}))

    if slug:
        try:
            t = catalog.get_by_slug(ctx.db, slug)
            needs = [r["code"] for r in t["required"]]
            if needs and not use_last:
                await state.update_data(template_id=t["id"], kind=t["kind"])
                await state.set_state(bc.Make.prompt)
                kb = InlineKeyboardBuilder()
                if last:
                    kb.row(InlineKeyboardButton(text="🖼 Взять последнюю работу", callback_data=f"mk:uselast:{last['id']}"))
                bc.cancel_row(kb)
                return await message.answer(f"{card_emoji(t)} <b>{esc(t['title'])}</b>\n📷 Пришлите фото — и сделаем.", reply_markup=kb.as_markup())
            await state.update_data(template_id=t["id"], kind=t["kind"])
            return await bc.ask_confirm(message, state, ctx, message.from_user.id)
        except DomainError:
            pass

    if kind == "video" and not use_last and last and bc.wants_last_result(text):
        await state.update_data(ref_order_id=last["id"])
    await bc.ask_model(message, state, ctx)


# ---------- отправка результата в чат ----------
class BotNotifier:
    def __init__(self, bot: Bot, ctx: AppContext):
        self.bot, self.ctx = bot, ctx

    async def notify_order(self, order: dict, with_menu: bool = True, with_actions: bool = True) -> None:
        chat_id = order["user_id"]
        if order["status"] == "failed":
            await self.bot.send_message(chat_id, "⚠️ " + esc(order.get("error_public") or orders.PUBLIC_FAIL_MESSAGE),
                                        reply_markup=main_menu(self.ctx))
            return
        if order["status"] != "done" or not order.get("result_path") or not Path(order["result_path"]).exists():
            return
        full = orders.get_user_order(self.ctx.db, chat_id, order["id"]) or order
        caption = f"✨ <b>{esc(full.get('title', ''))}</b>\nГотово! {BRAND}"
        if order.get("is_stub"):
            caption += "\n\n⚠️ Демо-режим: это не настоящая AI-генерация, API ещё не подключено."
        file = FSInputFile(order["result_path"])
        mime = order.get("result_mime") or ""
        kb = bc.result_kb(full).as_markup() if with_actions else None
        if mime == "image/gif":
            await self.bot.send_animation(chat_id, file, caption=caption, reply_markup=kb)
        elif mime.startswith("video/"):
            await self.bot.send_video(chat_id, file, caption=caption, reply_markup=kb)
        elif mime.startswith("audio/"):
            await self.bot.send_audio(chat_id, file, caption=caption, reply_markup=kb)
        else:
            await self.bot.send_photo(chat_id, file, caption=caption, reply_markup=kb)
        if with_menu and not with_actions:
            await self.bot.send_message(chat_id, MENU_TEXT, reply_markup=main_menu(self.ctx))


def build_bot(ctx: AppContext) -> tuple[Bot, Dispatcher]:
    bot = Bot(ctx.settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage(), ctx=ctx)
    router.message.outer_middleware(UserMiddleware())
    router.callback_query.outer_middleware(UserMiddleware())
    dp.include_router(router)
    return bot, dp


async def setup_bot_profile(bot: Bot, ctx: AppContext) -> None:
    """Имя, описание, команды и кнопка меню бота. Каждый шаг независим: сбой одного не мешает остальным."""

    problems: list[str] = []

    async def step(title: str, coro):
        try:
            await coro
        except Exception as e:  # Telegram ограничивает частоту смены имени/описания — это не критично
            log.warning("Профиль бота: «%s» не обновлён: %s", title, e)
            problems.append(f"{title}: {type(e).__name__}")

    async def name():
        if (await bot.get_my_name()).name != BRAND:
            await bot.set_my_name(name=BRAND)

    async def description():  # ставим всегда: описание в карточке бота Telegram кеширует
        await bot.set_my_description(description=BOT_DESCRIPTION)

    async def short():
        await bot.set_my_short_description(short_description=BOT_SHORT_DESCRIPTION)

    await step("имя", name())
    await step("описание", description())
    await step("короткое описание", short())
    await step("команды", bot.set_my_commands([
        BotCommand(command="start", description="🏠 Главное меню"),
        BotCommand(command="menu", description="✨ Каталог и приложение"),
        BotCommand(command="create", description="🪄 Создать"),
        BotCommand(command="profile", description="👤 Профиль"),
        BotCommand(command="history", description="🕘 Мои работы"),
        BotCommand(command="settings", description="⚙️ Настройки"),
    ]))
    from .services import site_settings
    site_settings.set_value(ctx.db, "bot_build", BUILD)
    site_settings.set_value(ctx.db, "bot_profile_problems", "; ".join(problems))
    log.info("Бот: сборка %s, приветствие «%s»", BUILD, WELCOME_TEXT.splitlines()[0])
    if ctx.settings.webapp_url:
        await step("кнопка меню", bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(text=BRAND, web_app=WebAppInfo(url=ctx.settings.webapp_url))))
