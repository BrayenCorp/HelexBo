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
from .services import categories, credits, events, methods, orders, payments, templates, users

log = logging.getLogger(__name__)
router = Router()

STATUS_ICON = {"created": "…", "processing": "…", "done": "✓", "failed": "!"}


class Flow(StatesGroup):
    waiting_photo = State()
    waiting_prompt = State()  # свободный запрос: сначала текст
    waiting_free_photo = State()  # затем фото (необязательно)


def esc(text: object) -> str:
    return html.escape(str(text))


BRAND = "Nolla AI"
BOT_DESCRIPTION = (
    "Nolla AI — AI-платформа для творчества в Telegram. Создавайте изображения, видео и озвучку с лучшими "
    "AI-моделями: эффекты, тренды, фотосессии, аватары и маркетинг. Первое фото и первое видео бесплатно."
)
BOT_SHORT_DESCRIPTION = "Изображения, видео и озвучка с помощью AI. Первое фото бесплатно."


def main_menu(ctx: AppContext) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if ctx.settings.webapp_url:  # платформа — главное: все разделы живут в приложении
        kb.row(InlineKeyboardButton(text=f"Открыть {BRAND}", web_app=WebAppInfo(url=ctx.settings.webapp_url)))
    else:  # WEBAPP_URL не задан — кнопка есть, но объясняет, что нужно сделать
        kb.row(InlineKeyboardButton(text=f"Открыть {BRAND}", callback_data="menu:app"))
    kb.row(InlineKeyboardButton(text="✦ Создать фото", callback_data="menu:photo"),
           InlineKeyboardButton(text="✦ Создать видео", callback_data="menu:video"))
    kb.row(InlineKeyboardButton(text="Мои токены", callback_data="menu:credits"),
           InlineKeyboardButton(text="Мои работы", callback_data="menu:works"))
    return kb.as_markup()


def price_label(t: dict, free: bool) -> str:
    return "бесплатно" if free else f"{t['price_credits']} ток."


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
    prof = users.profile(ctx.db, message.from_user.id)
    free = prof["free"]
    if not prof["welcomed"]:
        with ctx.db.read() as c:
            bonus = c.execute("SELECT COALESCE(SUM(delta),0) FROM credit_ledger WHERE user_id = ? AND reason = 'welcome_bonus'", (message.from_user.id,)).fetchone()[0]
        users.mark_welcomed(ctx.db, message.from_user.id)
        await message.answer(f"Добро пожаловать в {BRAND}! Ваш аккаунт создан." + (f"\nВаш стартовый бонус: {bonus} токенов." if bonus else ""))
    name = esc(message.from_user.first_name or "")
    text = (
        f"<b>{BRAND}</b>\n"
        f"{'Здравствуйте, ' + name + '.' if name else 'Здравствуйте.'}\n\n"
        "Изображения, видео и озвучка с помощью искусственного интеллекта. Все разделы — в приложении.\n\n"
        f"Подарок: первое фото — {'бесплатно' if free['photo'] else 'использовано'}, "
        f"первое видео — {'бесплатно' if free['video'] else 'использовано'}.\n\n"
        "Выберите, что создаём:"
    )
    await message.answer(text, reply_markup=main_menu(ctx))


@router.callback_query(F.data == "menu:home")
async def cb_home(call: CallbackQuery, state: FSMContext, ctx: AppContext):
    await state.clear()
    await call.message.answer("Главное меню:", reply_markup=main_menu(ctx))
    await call.answer()


@router.callback_query(F.data == "menu:app")
async def cb_app_missing(call: CallbackQuery):
    await call.answer("Mini App ещё не подключён: администратору нужно задать WEBAPP_URL.", show_alert=True)


@router.callback_query(F.data.in_({"menu:photo", "menu:video"}))
async def cb_choose_kind(call: CallbackQuery, state: FSMContext, ctx: AppContext):
    await state.clear()
    await ensure_user(ctx, call.from_user)
    kind = call.data.split(":")[1]
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="✦ Своё описание", callback_data=f"free:{kind}"))
    shown = 0
    for c in categories.list_public(ctx.db):
        n = len(templates.list_published(ctx.db, kind=kind, category=c["id"]))
        if n:
            kb.row(InlineKeyboardButton(text=f"{c['title']} · {n}", callback_data=f"cat:{kind}:{c['id']}"))
            shown += 1
    kb.row(InlineKeyboardButton(text="‹ В меню", callback_data="menu:home"))
    await call.message.answer("Опишите идею своими словами или выберите категорию:" if shown else "Опишите идею своими словами:", reply_markup=kb.as_markup())
    await call.answer()


@router.callback_query(F.data.startswith("cat:"))
async def cb_category(call: CallbackQuery, ctx: AppContext):
    _, kind, cid = call.data.split(":", 2)
    free = orders.free_status(ctx.db, call.from_user.id)[kind]
    items = templates.list_published(ctx.db, kind=kind, category=cid)
    kb = InlineKeyboardBuilder()
    for t in items:
        kb.row(InlineKeyboardButton(text=f"{t['title']} · {price_label(t, free)}", callback_data=f"tpl:{t['id']}"))
    kb.row(InlineKeyboardButton(text="‹ Категории", callback_data=f"menu:{kind}"))
    await call.message.answer("Выберите образ:", reply_markup=kb.as_markup())
    await call.answer()


@router.callback_query(F.data.startswith("tpl:"))
async def cb_template(call: CallbackQuery, state: FSMContext, ctx: AppContext):
    try:
        t = templates.get_published(ctx.db, int(call.data.split(":")[1]))
    except DomainError as e:
        return await call.answer(e.message, show_alert=True)
    free = orders.free_status(ctx.db, call.from_user.id)[t["kind"]]
    await state.set_state(Flow.waiting_photo)
    await state.update_data(template_id=t["id"])
    cost = "Бесплатно — ваша первая попытка." if free else f"Стоимость: {t['price_credits']} ток."
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="Отмена", callback_data="menu:home"))
    await call.message.answer(
        f"<b>{esc(t['title'])}</b>\n{esc(t['description'])}\n\n{cost}\n\n"
        "Отправьте фото: лицо хорошо видно, хороший свет. Для парных образов — фото, где вы вместе.",
        reply_markup=kb.as_markup(),
    )
    await call.answer()


async def _download(bot: Bot, file_id: str) -> bytes:
    buf = io.BytesIO()
    await bot.download(file_id, destination=buf)
    return buf.getvalue()


async def _submit(message: Message, state: FSMContext, ctx: AppContext, file_id: str | None, user=None, request_id: str | None = None):
    """Общая отправка заказа: по шаблону (template_id в состоянии) или свободный запрос (free_kind + prompt)."""
    data = await state.get_data()
    template_id, free_kind = data.get("template_id"), data.get("free_kind")
    user = user or message.from_user
    if not template_id and not free_kind:
        return await message.answer("Сначала выберите, что создаём.", reply_markup=main_menu(ctx))
    await ensure_user(ctx, user)
    image = await _download(message.bot, file_id) if file_id else None
    try:
        order, created = await asyncio.to_thread(
            lambda: orders.submit_generation(
                ctx.db, ctx.storage, user_id=user.id, template_id=template_id, kind=free_kind,
                request_id=request_id or f"tg:{message.chat.id}:{message.message_id}",  # повторная доставка апдейта не создаст второй заказ
                image_bytes=image, prompt=data.get("prompt", ""), source="bot", max_bytes=ctx.settings.max_upload_bytes,
            )
        )
    except InsufficientCredits as e:
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text="Пополнить токены", callback_data="menu:credits"))
        return await message.answer(f"{esc(e.message)}.", reply_markup=kb.as_markup())
    except DomainError as e:
        return await message.answer(esc(e.message))
    await state.clear()
    if not created:
        return
    note = "бесплатная попытка" if order["used_free"] else f"списано {order['price_credits']} ток."
    await message.answer(f"Создаём ({note}). Это займёт немного времени — пришлю результат сюда.")
    ctx.runner.schedule(order["id"])


# ---------- свободное описание ----------
@router.callback_query(F.data.startswith("free:"))
async def cb_free(call: CallbackQuery, state: FSMContext, ctx: AppContext):
    kind = call.data.split(":")[1]
    await state.clear()
    await state.set_state(Flow.waiting_prompt)
    await state.update_data(free_kind=kind, template_id=None)
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="Отмена", callback_data="menu:home"))
    await call.message.answer(
        "Опишите, что хотите получить (до 500 символов).\nНапример: <i>девушка в студии, мягкий свет, реалистично</i>",
        reply_markup=kb.as_markup(),
    )
    await call.answer()


@router.message(Flow.waiting_prompt, F.text)
async def got_prompt(message: Message, state: FSMContext):
    text = message.text.strip()
    if len(text) > 500:
        return await message.answer(f"Описание длиннее 500 символов ({len(text)}). Сократите, пожалуйста.")
    await state.update_data(prompt=text)
    await state.set_state(Flow.waiting_free_photo)
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="Создать без фото", callback_data="free_go"))
    kb.row(InlineKeyboardButton(text="Отмена", callback_data="menu:home"))
    await message.answer("Хотите добавить своё фото? Отправьте его — или создайте без фото.", reply_markup=kb.as_markup())


@router.callback_query(Flow.waiting_free_photo, F.data == "free_go")
async def free_go(call: CallbackQuery, state: FSMContext, ctx: AppContext):
    await _submit(call.message, state, ctx, None, user=call.from_user, request_id=f"tg:{call.message.chat.id}:{call.message.message_id}:go")
    await call.answer()


@router.message(Flow.waiting_free_photo, F.photo)
async def free_photo(message: Message, state: FSMContext, ctx: AppContext):
    await _submit(message, state, ctx, message.photo[-1].file_id)


@router.message(Flow.waiting_prompt)
@router.message(Flow.waiting_free_photo)
async def free_other(message: Message):
    await message.answer("Пришлите текстовое описание или фото. Для отмены нажмите «Отмена» выше.")


@router.message(Flow.waiting_photo, F.photo)
async def got_photo(message: Message, state: FSMContext, ctx: AppContext):
    await _submit(message, state, ctx, message.photo[-1].file_id)


@router.message(Flow.waiting_photo, F.document)
async def got_document(message: Message, state: FSMContext, ctx: AppContext):
    if not (message.document.mime_type or "").startswith("image/"):
        return await message.answer("Пришлите фото (изображение), пожалуйста.")
    await _submit(message, state, ctx, message.document.file_id)


@router.message(Flow.waiting_photo)
async def waiting_photo_other(message: Message):
    await message.answer("Жду ваше фото. Или нажмите «Отмена» выше.")


# ---------- кредиты и оплата ----------
@router.callback_query(F.data == "menu:credits")
async def cb_credits(call: CallbackQuery, ctx: AppContext):
    await ensure_user(ctx, call.from_user)
    prof = users.profile(ctx.db, call.from_user.id)
    ledger = credits.get_ledger(ctx.db, call.from_user.id, 5)
    names = {"purchase": "пополнение", "purchase_bonus": "бонус к пакету", "order_charge": "генерация", "order_refund": "возврат", "welcome_bonus": "стартовый бонус", "admin_adjust": "корректировка", "test_grant": "начисление"}
    lines = [f"{'+' if r['delta'] > 0 else ''}{r['delta']} — {names.get(r['reason'], r['reason'])}" for r in ledger]
    text = f"<b>Баланс: {prof['balance']} ток.</b>\n"
    text += f"Бесплатная попытка: фото — {'доступна' if prof['free']['photo'] else 'использована'}, видео — {'доступна' if prof['free']['video'] else 'использована'}\n"
    if lines:
        text += "\nПоследние операции:\n" + "\n".join(lines) + "\n"
    if ctx.settings.payments_mode == "test":
        text += "\nТестовый режим оплаты: реальные деньги не списываются."
    kb = InlineKeyboardBuilder()
    for p in payments.list_packages(ctx.db):
        kb.row(InlineKeyboardButton(text=f"{p['title']}: {p['credits']}{('+' + str(p['bonus'])) if p['bonus'] else ''} ток. — {p['price_stars']} ⭐", callback_data=f"buy:{p['id']}"))
    kb.row(InlineKeyboardButton(text="‹ В меню", callback_data="menu:home"))
    await call.message.answer(text, reply_markup=kb.as_markup())
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
        text = "Пока нет работ. Создайте первую — первое фото и первое видео бесплатно."
    else:
        text = "<b>Мои работы</b>\nНажмите, чтобы получить файл ещё раз:"
        for o in items:
            kb.row(InlineKeyboardButton(text=f"{STATUS_ICON[o['status']]} {o['title']}", callback_data=f"work:{o['id']}"))
    kb.row(InlineKeyboardButton(text="‹ В меню", callback_data="menu:home"))
    await call.message.answer(text, reply_markup=kb.as_markup())
    await call.answer()


@router.callback_query(F.data.startswith("work:"))
async def cb_work(call: CallbackQuery, ctx: AppContext):
    o = orders.get_user_order(ctx.db, call.from_user.id, int(call.data.split(":")[1]))
    if o is None:
        return await call.answer("Работа не найдена", show_alert=True)
    if o["status"] in ("created", "processing"):
        return await call.answer("Ещё создаётся — результат придёт в чат.", show_alert=True)
    await BotNotifier(call.bot, ctx).notify_order(o)
    await call.answer()


# ---------- команды: /create /profile /history /settings ----------
@router.message(Command("create"))
async def cmd_create(message: Message, state: FSMContext, ctx: AppContext):
    await state.clear()
    _log_command(ctx, message.from_user.id, "create")
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="✦ Создать фото", callback_data="menu:photo"), InlineKeyboardButton(text="✦ Создать видео", callback_data="menu:video"))
    if ctx.settings.webapp_url:
        kb.row(InlineKeyboardButton(text=f"Открыть {BRAND}", web_app=WebAppInfo(url=ctx.settings.webapp_url)))
    await message.answer("Что создаём?", reply_markup=kb.as_markup())


@router.message(Command("profile"))
async def cmd_profile(message: Message, ctx: AppContext):
    _log_command(ctx, message.from_user.id, "profile")
    prof = users.profile(ctx.db, message.from_user.id)
    done = orders.count_done_by_kind(ctx.db, message.from_user.id)
    text = (f"<b>Профиль</b>\nТариф: {'PRO' if prof['is_pro'] else 'Бесплатный'}\nБаланс: {prof['balance']} ток.\n"
            f"Генераций: {done['photo'] + done['video'] + done['audio']} (фото {done['photo']}, видео {done['video']}, аудио {done['audio']})")
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="Пополнить токены", callback_data="menu:credits"))
    await message.answer(text, reply_markup=kb.as_markup())


@router.message(Command("history"))
async def cmd_history(message: Message, ctx: AppContext):
    _log_command(ctx, message.from_user.id, "history")
    items = orders.list_user_orders(ctx.db, message.from_user.id, 8)
    kb = InlineKeyboardBuilder()
    if not items:
        text = "Пока нет работ. Первое фото и первое видео — бесплатно."
    else:
        text = "<b>История генераций</b>\nНажмите, чтобы получить файл ещё раз:"
        for o in items:
            kb.row(InlineKeyboardButton(text=f"{STATUS_ICON[o['status']]} {o['title']}", callback_data=f"work:{o['id']}"))
    await message.answer(text, reply_markup=kb.as_markup())


def _settings_kb(on: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=("Результаты в чат: включено ✓" if on else "Результаты в чат: выключено"), callback_data=f"set:notify:{0 if on else 1}"))
    return kb.as_markup()


@router.message(Command("settings"))
async def cmd_settings(message: Message, ctx: AppContext):
    _log_command(ctx, message.from_user.id, "settings")
    on = users.profile(ctx.db, message.from_user.id)["notify_chat"]
    await message.answer("<b>Настройки</b>\nПрисылать готовые фото и видео в этот чат?", reply_markup=_settings_kb(on))


@router.callback_query(F.data.startswith("set:notify:"))
async def cb_set_notify(call: CallbackQuery, ctx: AppContext):
    on = call.data.endswith(":1")
    users.set_notify_chat(ctx.db, call.from_user.id, on)
    await call.message.edit_reply_markup(reply_markup=_settings_kb(on))
    await call.answer("Сохранено")


# ---------- отправка результата в чат ----------
class BotNotifier:
    def __init__(self, bot: Bot, ctx: AppContext):
        self.bot, self.ctx = bot, ctx

    async def notify_order(self, order: dict, with_menu: bool = True) -> None:
        chat_id = order["user_id"]
        if order["status"] == "failed":
            await self.bot.send_message(chat_id, esc(order.get("error_public") or orders.PUBLIC_FAIL_MESSAGE),
                                        reply_markup=main_menu(self.ctx))
            return
        if order["status"] != "done" or not order.get("result_path") or not Path(order["result_path"]).exists():
            return
        full = orders.get_user_order(self.ctx.db, chat_id, order["id"]) or order
        caption = f"<b>{esc(full.get('title', ''))}</b>\nГотово. {BRAND}"
        if order.get("is_stub"):
            caption += "\n\nТЕСТОВЫЙ РЕЖИМ: это не настоящая AI-генерация, API ещё не подключено."
        file = FSInputFile(order["result_path"])
        mime = order.get("result_mime") or ""
        if mime == "image/gif":
            await self.bot.send_animation(chat_id, file, caption=caption)
        elif mime.startswith("video/"):
            await self.bot.send_video(chat_id, file, caption=caption)
        elif mime.startswith("audio/"):
            await self.bot.send_document(chat_id, file, caption=caption)
        else:
            await self.bot.send_photo(chat_id, file, caption=caption)
        if with_menu:
            await self.bot.send_message(chat_id, "Что дальше?", reply_markup=main_menu(self.ctx))


def build_bot(ctx: AppContext) -> tuple[Bot, Dispatcher]:
    bot = Bot(ctx.settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage(), ctx=ctx)
    router.message.outer_middleware(UserMiddleware())
    router.callback_query.outer_middleware(UserMiddleware())
    dp.include_router(router)
    return bot, dp


async def setup_bot_profile(bot: Bot, ctx: AppContext) -> None:
    """Имя, описание, команды и кнопка меню бота. Каждый шаг независим: сбой одного не мешает остальным."""

    async def step(title: str, coro):
        try:
            await coro
        except Exception as e:  # Telegram ограничивает частоту смены имени/описания — это не критично
            log.warning("Профиль бота: «%s» не обновлён: %s", title, e)

    async def name():
        if (await bot.get_my_name()).name != BRAND:
            await bot.set_my_name(name=BRAND)

    async def description():
        if (await bot.get_my_description()).description != BOT_DESCRIPTION:
            await bot.set_my_description(description=BOT_DESCRIPTION)

    async def short():
        if (await bot.get_my_short_description()).short_description != BOT_SHORT_DESCRIPTION:
            await bot.set_my_short_description(short_description=BOT_SHORT_DESCRIPTION)

    await step("имя", name())
    await step("описание", description())
    await step("короткое описание", short())
    await step("команды", bot.set_my_commands([
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="menu", description="Открыть меню"),
        BotCommand(command="create", description="Создать фото, видео или аудио"),
        BotCommand(command="profile", description="Профиль и баланс"),
        BotCommand(command="history", description="История генераций"),
        BotCommand(command="settings", description="Настройки"),
    ]))
    if ctx.settings.webapp_url:
        await step("кнопка меню", bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(text=BRAND, web_app=WebAppInfo(url=ctx.settings.webapp_url))))
