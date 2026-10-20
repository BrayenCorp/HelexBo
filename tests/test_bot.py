"""Бот как полноценный интерфейс Nolla AI: фото, видео, аудио, понимание обычных сообщений, общая база.

Тесты идут через настоящие сервисы и базу: заказ, созданный в боте, виден и в приложении, и в админке.
Telegram заменён лёгкой заглушкой (tests/stub/aiogram), сам aiogram для этого не нужен.
"""
import asyncio
import inspect
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "stub"))

try:
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.state import State
    from aiogram.types import CallbackQuery, Message
    from app import bot as B
except ImportError as e:  # настоящий aiogram без заглушки — тогда пропускаем
    B = None
    SKIP = str(e)

from app.services import admin_users, credits, generation, orders, users
from tests.helpers import BaseTest, make_photo


@unittest.skipIf(B is None, "нужен aiogram или заглушка")
class BotTest(BaseTest):
    UID = 7

    def setUp(self):
        super().setUp()
        from app.ai.registry import ProviderRegistry
        from app.config import Settings
        from app.context import AppContext
        from app.security import AdminAccess

        outer = self

        class Runner:
            def __init__(self):
                self.scheduled = []
                self.jobs = []  # снимок заказа до генерации: исходное фото после неё удаляется

            def schedule(self, order_id):
                self.scheduled.append(order_id)
                self.jobs.append(orders.get_order(outer.db, order_id))

            def schedule_avatar(self, avatar_id):
                pass

        self.bot = B.Bot("123:abc")
        self.bot.files = {"file-1": make_photo((600, 800))}
        self.runner = Runner()
        self.ctx = AppContext(Settings(webapp_url="https://app.example", payments_mode="test"), self.db, self.storage,
                              self.mock, self.runner, AdminAccess(frozenset(), frozenset()))
        self.ctx.bot_username = "nolla_bot"
        self.state = FSMContext()
        self.outbox = []
        self.user = type("U", (), {"id": self.UID, "username": "brayen", "first_name": "Брайен", "last_name": None, "language_code": "ru"})()
        users.upsert_user(self.db, self.UID, "brayen", "Брайен")
        users.register(self.db, self.UID)
        self.add_balance(self.UID, 500)

    # ---------- доставка события обработчику, как это делает aiogram ----------
    def _msg(self, text=None, photo=None, caption=None):
        return Message(chat_id=self.UID, message_id=len(self.outbox) + 1, text=text, caption=caption,
                       photo=[type("P", (), {"file_id": photo})()] if photo else None,
                       from_user=self.user, bot=self.bot, outbox=self.outbox)

    async def _deliver(self, event, section):
        state = await self.state.get_state()
        for filters, fn in section.handlers:
            ok = True
            for f in filters:
                ok = (state == str(f)) if isinstance(f, State) else f(event)
                if not ok:
                    break
            if not ok:
                continue
            kwargs = {}
            for name in inspect.signature(fn).parameters:
                if name in ("message", "call", "query"):
                    continue
                kwargs[name] = {"state": self.state, "ctx": self.ctx, "bot": self.bot}.get(name)
            return await fn(event, **kwargs)
        return None

    def _work(self):
        """Доводим созданные заказы до конца и присылаем результат в чат — как это делает Runner."""
        while self.runner.scheduled:
            oid = self.runner.scheduled.pop(0)
            generation.process_order(self.db, self.storage, self.mock, oid)
            o = orders.get_user_order(self.db, self.UID, oid)
            asyncio.run(B.BotNotifier(self.bot, self.ctx).notify_order(o))

    def send(self, text=None, photo=None, caption=None):
        """Сообщение от пользователя: сначала middleware (учёт пользователя), потом обработчик."""
        msg = self._msg(text, photo, caption)
        asyncio.run(B.UserMiddleware()(lambda e, d: self._deliver(e, B.router.message), msg, {"ctx": self.ctx}))
        self._work()
        return self.last()

    def tap(self, data):
        """Нажатие кнопки."""
        call = CallbackQuery(data=data, from_user=self.user, message=self._msg(), bot=self.bot)
        asyncio.run(B.UserMiddleware()(lambda e, d: self._deliver(e, B.router.callback_query), call, {"ctx": self.ctx}))
        self._work()
        return self.last()

    def last(self):
        return self.outbox[-1] if self.outbox else {"text": "", "markup": None}

    def labels(self, out=None):
        m = (out or self.last())["markup"]
        return [b.text for row in (m.inline_keyboard if m else []) for b in row]

    def data_of(self, needle, out=None):
        m = (out or self.last())["markup"]
        for row in (m.inline_keyboard if m else []):
            for b in row:
                if needle.casefold() in (b.text or "").casefold():
                    return b.callback_data
        raise AssertionError(f"Кнопки «{needle}» нет среди {self.labels(out)}")

    def my_orders(self):
        return orders.list_user_orders(self.db, self.UID, 50)

    # ------------------------------------------------------------------ тесты
    def test_start_menu(self):
        self.send("/start")
        self.assertTrue(any("Добро пожаловать в Nolla AI" in o["text"] for o in self.outbox), self.outbox)
        labels = self.labels()
        for want in ("📷 Создать фото", "🎬 Создать видео", "💡 Посмотреть идеи", "🖼 Мои генерации"):
            self.assertIn(want, labels)
        self.assertNotIn("🎙 Создать аудио", labels)  # аудио не делаем
        self.assertTrue(any("Открыть" in l for l in labels))
        web = [b for row in self.last()["markup"].inline_keyboard for b in row if b.web_app]
        self.assertEqual(web[0].web_app.url, "https://app.example")

    def test_photo_flow_with_model_and_price(self):
        self.tap("mk:new:photo")
        self.assertIn("Опишите", self.last()["text"])
        self.send("кот в космосе")
        self.assertIn("Выберите модель", self.last()["text"])
        pick = self.data_of("Nano Banana 2 ·")
        self.tap(pick)
        self.assertIn("Стоимость", self.last()["text"])
        self.assertIn("кот в космосе", self.last()["text"])
        self.tap(self.data_of("Создать"))
        self.assertIn("Создаём изображение", self.last()["text"])
        o = self.my_orders()[0]
        self.assertEqual((o["kind"], o["source"], o["status"]), ("photo", "bot", "done"))
        self.assertEqual(o["prompt"], "кот в космосе")
        self.assertTrue(self.balance_matches_ledger(self.UID))
        sent = [s for s in self.bot.sent if s["kind"] == "photo"]
        self.assertEqual(len(sent), 1)
        self.assertIn("Готово", sent[0]["caption"])
        actions = [b.text for row in sent[0]["reply_markup"].inline_keyboard for b in row]
        for want in ("⬇️ Скачать", "🔁 Создать заново", "✏️ Изменить", "✨ Вариация", "🎬 Сделать видео"):
            self.assertIn(want, actions)

    def test_audio_is_off(self):
        before = len(self.outbox)
        self.tap("mk:new:audio")
        self.assertEqual(len(self.outbox), before)  # ничего не предлагаем
        self.assertEqual(self.my_orders(), [])

    def test_video_from_photo(self):
        self.tap("mk:new:video")
        self.send(photo="file-1")
        self.assertIn("Выберите модель", self.last()["text"])
        self.tap(self.data_of("Seedance"))
        self.tap(self.data_of("Создать"))
        o = self.my_orders()[0]
        self.assertEqual((o["kind"], o["source"], o["status"]), ("video", "bot", "done"))
        self.assertEqual(self.bot.sent[-1]["kind"], "animation")

    def test_plain_message_is_understood(self):
        self.send("Создай фотографию девушки в чёрном костюме на фоне ночного города")
        self.assertIn("Выберите модель", self.last()["text"])
        self.tap(self.data_of("Nano Banana 2 ·"))
        self.tap(self.data_of("Создать"))
        self.assertEqual(self.my_orders()[0]["kind"], "photo")

        self.send("Озвучь этот текст мужским голосом")
        self.assertNotIn("Выберите голос", self.last()["text"])

    def test_context_last_image_for_video(self):
        self.send("создай фото города")
        self.tap(self.data_of("Nano Banana 2 ·"))
        self.tap(self.data_of("Создать"))
        first = self.my_orders()[0]
        self.assertEqual(first["status"], "done")
        self.send("Теперь сделай из него видео")
        self.assertIn("Выберите модель", self.last()["text"])
        self.tap(self.data_of("Seedance 2.5"))
        self.tap(self.data_of("Создать"))
        o = self.my_orders()[0]
        self.assertEqual(o["kind"], "video")
        self.assertIsNotNone(self.runner.jobs[-1]["input_path"])  # взял прошлую картинку как исходник

    def test_result_buttons_make_new_work(self):
        self.send("создай фото моря")
        self.tap(self.data_of("Nano Banana 2 ·"))
        self.tap(self.data_of("Создать"))
        done = self.my_orders()[0]
        self.tap(f"res:var:{done['id']}")
        self.assertIn("Стоимость", self.last()["text"])
        self.tap(self.data_of("Создать"))
        self.assertEqual(len(self.my_orders()), 2)
        self.tap(f"res:edit:{done['id']}")
        self.assertIn("Что изменить", self.last()["text"])
        self.send("добавь закат")
        self.tap(self.data_of("Nano Banana 2 ·"))
        self.tap(self.data_of("Создать"))
        self.assertEqual(len(self.my_orders()), 3)
        self.assertTrue(self.balance_matches_ledger(self.UID))

    def test_photo_without_caption_asks_what_to_do(self):
        self.send(photo="file-1")
        self.assertIn("Что с ним сделать", self.last()["text"])
        self.assertIn("🎬 Сделать видео", self.labels())
        self.tap("mk:withphoto:video")
        self.assertIn("Выберите модель", self.last()["text"])

    def test_tool_from_plain_text(self):
        self.send("сделай 9 ракурсов этого фото")
        self.assertTrue("Пришлите фото" in self.last()["text"] or "Стоимость" in self.last()["text"])

    def test_ideas_are_taken_from_showcase(self):
        from app.services import templates
        templates.create(self.db, {"title": "Ночная фотосессия", "kind": "photo", "section": "idea", "tag": "portrait",
                                   "price_credits": 14, "is_published": True, "prompt": "night city portrait"})
        self.tap("mk:ideas:0")
        self.assertIn("Ночная фотосессия", " ".join(self.labels()))
        self.tap(self.data_of("Ночная фотосессия"))
        self.assertIn("Стоимость", self.last()["text"])
        self.tap(self.data_of("Создать"))
        self.assertEqual(self.my_orders()[0]["status"], "done")

    def test_bot_user_and_orders_visible_to_admin(self):
        self.send("/start")
        self.send("создай фото собаки")
        self.tap(self.data_of("Nano Banana 2 ·"))
        self.tap(self.data_of("Создать"))
        row = [u for u in admin_users.users_list(self.db)["items"] if u["tg_id"] == self.UID][0]
        self.assertEqual((row["generations"], row["photos"], row["via_bot"]), (1, 1, 1))
        self.assertIsNotNone(row["last_seen_at"])
        from datetime import date, timedelta
        from app.services import analytics
        st = analytics.bot_stats(self.db, date.today() - timedelta(days=1), date.today())
        self.assertEqual((st["users_total"], st["generations_total"], st["photo"]), (1, 1, 1))
        self.assertGreaterEqual(st["started"], 1)

    def test_blocked_user_gets_nothing(self):
        with self.db.tx() as c:
            c.execute("UPDATE users SET status = 'blocked' WHERE tg_id = ?", (self.UID,))
        self.send("создай фото")
        self.assertIn("заблокирован", self.last()["text"])
        self.assertEqual(self.my_orders(), [])

    def test_not_enough_tokens_points_to_app(self):
        with self.db.tx() as c:
            credits.apply(c, self.UID, -credits.get_balance(self.db, self.UID), "admin_adjust")
        orders.submit_generation  # заказ не создастся: бесплатная попытка уже есть, но баланс нулевой
        self.send("создай фото звезды")
        self.tap(self.data_of("Nano Banana 2.1"))
        self.tap(self.data_of("Создать"))
        if self.my_orders():  # первая попытка бесплатна — тогда проверяем вторую
            self.send("создай фото ещё раз")
            self.tap(self.data_of("Nano Banana 2.1"))
            self.tap(self.data_of("Создать"))
        self.assertIn("токен", self.last()["text"].casefold())

    def test_version_command_reports_build(self):
        self.send("/version")
        text = self.last()["text"]
        self.assertIn(B.BUILD, text)
        self.assertIn("Добро пожаловать в Nolla AI.", text)

    def test_only_one_welcome_in_code(self):
        """Единственный источник приветствия: /start и повторный /start дают один и тот же текст."""
        self.send("/start")
        first = [o["text"] for o in self.outbox]
        self.outbox.clear()
        self.send("/start")
        self.assertEqual(len(self.outbox), 1)
        self.assertEqual(self.outbox[0]["text"], B.WELCOME_TEXT)
        self.assertTrue(any(t == B.WELCOME_TEXT for t in first))
