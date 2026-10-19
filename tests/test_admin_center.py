"""Центр аналитики и управления: регистрация, источники, токены, модели, аналитика на реальных данных, действия админа."""
import os
import sqlite3
import tempfile
from datetime import timedelta

from app.db import SCHEMA, Database, init_db
from app.errors import DomainError, InsufficientCredits
from app.services import (
    admin_lists, admin_users, analytics, content, credits, exports, generation, methods, models, orders, payments, site_settings, sources, users,
)
from tests.helpers import BaseTest, make_photo


def buy(test, user_id=1, pkg="p10", charge=None, provider="stars"):
    p = payments.create_payment(test.db, user_id, pkg, provider)
    payments.confirm_payment(test.db, p["payload"], provider=provider, provider_charge_id=charge or f"c{p['id']}",
                             paid_stars=p["amount_stars"] if provider == "stars" else None)
    return p


def free(test, rid, kind="photo", **kw):
    return orders.submit_generation(test.db, test.storage, user_id=kw.pop("user_id", 1), request_id=rid, source="app", kind=kind, **kw)


class RegistrationTest(BaseTest):
    def test_registration_required_for_generation(self):
        users.upsert_user(self.db, 5, "new", "Новый")
        with self.assertRaises(DomainError) as cm:
            free(self, "a", prompt="x", user_id=5)
        self.assertEqual(cm.exception.code, "registration_required")
        users.register(self.db, 5)
        free(self, "a", prompt="x", user_id=5)

    def test_welcome_bonus_only_when_enabled_and_only_once(self):
        users.upsert_user(self.db, 6, "a", "A")
        u, newly = users.register(self.db, 6)
        self.assertTrue(newly)
        self.assertEqual(credits.get_balance(self.db, 6), 0)  # по умолчанию бонус выключен
        site_settings.update(self.db, {"welcome_bonus": "100"})
        users.upsert_user(self.db, 7, "b", "B")
        users.register(self.db, 7)
        users.register(self.db, 7)  # повтор не начисляет второй раз
        self.assertEqual(credits.get_balance(self.db, 7), 100)
        self.assertTrue(self.balance_matches_ledger(7))

    def test_blocked_user_cannot_generate(self):
        admin_users.act(self.db, {"id": 99, "username": "adm"}, 1, "block", confirm=True)
        with self.assertRaises(DomainError) as cm:
            free(self, "a", prompt="x")
        self.assertEqual(cm.exception.code, "blocked")
        admin_users.act(self.db, {"id": 99}, 1, "unblock", confirm=True)
        free(self, "b", prompt="x")

    def test_existing_users_are_registered_by_migration(self):
        with tempfile.TemporaryDirectory() as d:
            db = Database(os.path.join(d, "old.db"))
            with db.read() as conn:
                conn.executescript(SCHEMA)
                conn.execute("DELETE FROM settings WHERE key = 'registration_v5'")
                conn.execute("INSERT INTO users (tg_id, first_name, created_at) VALUES (9, 'Старый', '2026-01-05T10:00:00+00:00')")
            init_db(db)
            self.assertTrue(users.profile(db, 9)["registered"])
            self.assertTrue(users.profile(db, 9)["welcomed"])  # приветствие старым пользователям не показываем


class SourcesTest(BaseTest):
    def test_source_only_from_real_start_param(self):
        users.upsert_user(self.db, 10, "a", "A", start_param="src_tiktok_spring_video1")
        u = users.get_user(self.db, 10)
        self.assertEqual((u["source"], u["campaign"], u["material"]), ("tiktok", "spring", "video1"))
        self.assertEqual(sources.label(u["source"]), "TikTok")
        users.upsert_user(self.db, 11, "b", "B")  # параметра не было
        self.assertIsNone(users.get_user(self.db, 11)["source"])
        self.assertEqual(sources.label(None), "Не определён")

    def test_referral_link_sets_referrer_and_ignores_self_or_unknown(self):
        users.upsert_user(self.db, 12, "c", "C", start_param="ref_1")
        u = users.get_user(self.db, 12)
        self.assertEqual((u["source"], u["referrer_id"]), ("referral", 1))
        users.upsert_user(self.db, 13, "d", "D", start_param="ref_13")  # сам себя
        users.upsert_user(self.db, 14, "e", "E", start_param="ref_999")  # такого нет
        self.assertIsNone(users.get_user(self.db, 13)["referrer_id"])
        self.assertIsNone(users.get_user(self.db, 14)["referrer_id"])

    def test_source_is_not_overwritten(self):
        users.upsert_user(self.db, 15, "f", "F", start_param="src_vk")
        users.upsert_user(self.db, 15, "f", "F", start_param="src_instagram")
        self.assertEqual(users.get_user(self.db, 15)["source"], "vk")


class ModelsAndVariantsTest(BaseTest):
    def test_model_price_used_and_inactive_model_rejected(self):
        free(self, "free", prompt="x")  # занимаем бесплатную
        self.add_balance(1, 50)
        m = models.public_list(self.db, "photo")[0]
        o, _ = free(self, "a", prompt="x", model_id=m["id"])
        self.assertEqual(o["price_credits"], m["price_credits"])
        self.assertEqual(o["model"], "image-default")
        inactive = [x for x in models.admin_list(self.db) if not x["is_active"]][0]
        with self.assertRaises(DomainError):
            free(self, "b", kind="video", prompt="x", model_id=inactive["id"])

    def test_model_crud_validation_and_hide_when_used(self):
        with self.assertRaises(DomainError):
            models.create(self.db, {"name": "X", "kind": "photo", "provider_key": "nope"})
        m = models.create(self.db, {"name": "Новая", "kind": "photo", "provider_key": "image-default", "price_credits": 5, "is_active": True})
        self.assertIn(m["id"], [x["id"] for x in models.public_list(self.db)])
        self.assertTrue(models.delete(self.db, m["id"])["deleted"])
        m2 = models.public_list(self.db, "photo")[0]
        free(self, "a", prompt="x", model_id=m2["id"])
        self.assertTrue(models.delete(self.db, m2["id"])["hidden"])

    def test_variants_charge_each_and_check_balance_upfront(self):
        free(self, "free", prompt="x")
        self.add_balance(1, 5)
        with self.assertRaises(InsufficientCredits):  # 3 варианта × 2 токена = 6 > 5, ничего не создаётся
            orders.submit_variants(self.db, self.storage, count=3, user_id=1, request_id="v", source="app", kind="photo", prompt="y")
        self.assertEqual(credits.get_balance(self.db, 1), 5)
        res = orders.submit_variants(self.db, self.storage, count=2, user_id=1, request_id="v2", source="app", kind="photo", prompt="y")
        self.assertEqual(len(res), 2)
        self.assertEqual(credits.get_balance(self.db, 1), 1)
        again = orders.submit_variants(self.db, self.storage, count=2, user_id=1, request_id="v2", source="app", kind="photo", prompt="y")
        self.assertEqual([c for _, c in again], [False, False])  # повтор запроса ничего не списывает
        self.assertEqual(credits.get_balance(self.db, 1), 1)

    def test_variants_limited_by_setting(self):
        site_settings.update(self.db, {"max_variants": "2"})
        self.add_balance(1, 100)
        res = orders.submit_variants(self.db, self.storage, count=9, user_id=1, request_id="m", source="app", kind="photo", prompt="y")
        self.assertEqual(len(res), 2)


class PaymentsTest(BaseTest):
    def test_bonus_credited_separately_and_once(self):
        pkg = payments.create_package(self.db, {"title": "Б", "credits": 100, "price_stars": 50, "bonus": 20})
        p = payments.create_payment(self.db, 1, pkg["id"], "stars")
        for _ in range(2):
            payments.confirm_payment(self.db, p["payload"], provider="stars", provider_charge_id="x1", paid_stars=50)
        self.assertEqual(credits.get_balance(self.db, 1), 120)
        s = credits.summary(self.db, 1)
        self.assertEqual((s["bought"], s["bonus"]), (100, 20))
        self.assertTrue(self.balance_matches_ledger())

    def test_payments_table_accepts_new_methods(self):
        pkg = payments.create_package(self.db, {"title": "Р", "credits": 10, "price_stars": 5, "price_rub": 199})
        p = payments.create_payment(self.db, 1, pkg["id"], "sbp")
        self.assertEqual((p["currency"], p["amount"], p["amount_stars"]), ("RUB", 199.0, 0))
        with self.assertRaises(DomainError):
            payments.create_payment(self.db, 1, "p10", "sbp")  # нет цены в рублях

    def test_unconnected_methods_never_shown_as_working(self):
        from app.config import Settings
        st = Settings(payments_mode="stars")
        v = methods.for_users(self.db, st, bot_present=True)
        self.assertEqual([m["code"] for m in v["available"]], ["stars"])  # СБП и карта выключены, test не в режиме test
        methods.update(self.db, "sbp", {"status": "on"})
        self.assertNotIn("sbp", [m["code"] for m in methods.for_users(self.db, st, True)["available"]])  # включён, но не подключён
        methods.update(self.db, "card", {"status": "soon"})
        self.assertIn("card", [m["code"] for m in methods.for_users(self.db, st, True)["soon"]])
        self.assertEqual([m["code"] for m in methods.for_users(self.db, Settings(payments_mode="test"), False)["available"]], ["test"])
        self.assertEqual(methods.for_users(self.db, Settings(payments_mode="stars"), bot_present=False)["available"], [])

    def test_old_payments_table_is_rebuilt_without_losing_rows(self):
        with tempfile.TemporaryDirectory() as d:
            db = Database(os.path.join(d, "old.db"))
            with db.read() as conn:
                conn.executescript(SCHEMA)
                conn.executescript("""DROP TABLE payments; CREATE TABLE payments (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
                  package_id TEXT NOT NULL, credits INTEGER NOT NULL, amount_stars INTEGER NOT NULL,
                  provider TEXT NOT NULL CHECK (provider IN ('test', 'stars')), status TEXT NOT NULL CHECK (status IN ('pending', 'paid', 'failed')),
                  payload TEXT NOT NULL UNIQUE, provider_charge_id TEXT UNIQUE, created_at TEXT NOT NULL, paid_at TEXT);
                  INSERT INTO users (tg_id, created_at) VALUES (1, 'x');
                  INSERT INTO payments (user_id, package_id, credits, amount_stars, provider, status, payload, created_at) VALUES (1, 'p10', 10, 50, 'stars', 'paid', 'pl', 'x');""")
            init_db(db)
            with db.read() as conn:
                row = conn.execute("SELECT provider, status, amount, currency, bonus FROM payments").fetchone()
                conn.execute("PRAGMA foreign_keys = OFF")
                conn.execute("INSERT INTO payments (user_id, package_id, credits, amount_stars, provider, status, payload, created_at) VALUES (1,'p10',1,0,'sbp','refunded','pl2','x')")
            self.assertEqual((row["provider"], row["status"], row["currency"], row["bonus"]), ("stars", "paid", "XTR", 0))
            self.assertEqual(row["amount"], 50)


class AnalyticsTest(BaseTest):
    def period(self):
        return analytics.resolve_period("today")

    def test_numbers_come_from_real_data_and_are_zero_when_empty(self):
        s, e = self.period()
        ov = analytics.overview(self.db, s, e, 0.013)
        self.assertEqual(ov["money"]["revenue_stars"], 0)
        self.assertEqual(ov["generations"]["total"], 0)
        buy(self)
        buy(self, provider="test")  # тестовая оплата в выручку не входит
        o, _ = free(self, "a", prompt="x")
        generation.process_order(self.db, self.storage, self.mock, o["id"])
        o2, _ = free(self, "v", kind="video", prompt="y")
        generation.process_order(self.db, self.storage, self.live, o2["id"])  # ошибка
        ov = analytics.overview(self.db, s, e, 0.013)
        self.assertEqual(ov["money"]["revenue_stars"], 50)
        self.assertEqual(ov["money"]["purchases"], 1)
        self.assertEqual(ov["money"]["avg_check"], 50)
        self.assertEqual((ov["generations"]["total"], ov["generations"]["photo"], ov["generations"]["video"]), (2, 1, 1))
        self.assertEqual((ov["generations"]["success"], ov["generations"]["errors"]), (1, 1))
        self.assertEqual(ov["users"]["total"], 1)
        self.assertEqual((ov["users"]["new"], ov["users"]["active"]), (1, 1))
        self.assertEqual(ov["tokens"]["sold"], 10)

    def test_series_zero_filled_and_matches_overview(self):
        buy(self)
        s, e = analytics.resolve_period("7d")
        ser = analytics.series(self.db, s, e)
        self.assertEqual(len(ser["days"]), 7)
        self.assertEqual(sum(ser["revenue"]), 50)
        self.assertEqual(ser["users_new"][-1], 1)
        self.assertEqual(sum(ser["users_new"][:-1]), 0)

    def test_funnel_stages_and_percentages(self):
        users.upsert_user(self.db, 2, "b", "B")
        users.register(self.db, 2)
        free(self, "a", prompt="x")
        free(self, "b", prompt="y", kind="video")
        buy(self)
        s, e = analytics.resolve_period("today")
        f = analytics.funnel(self.db, s, e)
        by = {x["stage"]: x for x in f["stages"]}
        self.assertEqual(f["cohort_size"], 2)
        self.assertEqual(by["Создал первую генерацию"]["count"], 1)
        self.assertEqual(by["Создал вторую генерацию"]["count"], 1)
        self.assertEqual(by["Купил токены"]["count"], 1)
        self.assertEqual(by["Создал первую генерацию"]["of_total"], 50.0)
        self.assertEqual(by["Запустил бота"]["count"], 0)  # событий ещё нет — честный ноль, не выдумка

    def test_retention_none_until_enough_days_passed(self):
        r = analytics.retention(self.db, 30)
        row = r["rows"][0]
        self.assertEqual(row["size"], 1)
        self.assertIsNone(row["d1"])  # сегодняшняя когорта: «день 1» ещё не наступил

    def test_popularity_and_providers(self):
        self.add_balance(1, 20)
        o, _ = self.submit("a")
        generation.process_order(self.db, self.storage, self.mock, o["id"])
        free(self, "f", prompt="свободный")
        s, e = analytics.resolve_period("today")
        pop = analytics.popularity(self.db, s, e)
        self.assertEqual(pop["categories"][0]["uses"], 1)
        self.assertEqual(pop["categories"][0]["success_rate"], 100.0)
        self.assertEqual(pop["freeform"]["uses"], 1)
        prov = analytics.providers(self.db, s, e)
        self.assertEqual(sum(p["generations"] for p in prov), 2)

    def test_bad_period_rejected(self):
        with self.assertRaises(DomainError):
            analytics.resolve_period("custom", "2026-02-01", "2026-01-01")
        with self.assertRaises(DomainError):
            analytics.resolve_period("forever")


class AdminUsersTest(BaseTest):
    ADMIN = {"id": 99, "username": "boss", "first_name": "Босс"}

    def test_list_filters_search_and_pagination(self):
        for i in range(2, 8):
            users.upsert_user(self.db, i, f"user{i}", f"Имя{i}")
        buy(self)
        self.assertEqual(admin_users.users_list(self.db)["total"], 7)
        self.assertEqual(len(admin_users.users_list(self.db, size=3, page=2)["items"]), 3)
        self.assertEqual(admin_users.users_list(self.db, flt="paying")["total"], 1)
        self.assertEqual(admin_users.users_list(self.db, flt="nonpaying")["total"], 6)
        self.assertEqual(admin_users.users_list(self.db, q="user5")["items"][0]["tg_id"], 5)
        self.assertEqual(admin_users.users_list(self.db, q="имя3")["total"], 1)  # поиск без учёта регистра в кириллице
        users.set_pro(self.db, 2, True)
        self.assertEqual(admin_users.users_list(self.db, flt="pro")["total"], 1)
        with self.assertRaises(DomainError):
            admin_users.users_list(self.db, flt="hack; drop")

    def test_profile_has_money_tokens_generations_timeline(self):
        buy(self)
        o, _ = free(self, "a", prompt="x")
        generation.process_order(self.db, self.storage, self.mock, o["id"])
        p = admin_users.user_profile(self.db, 1, 0.013)
        self.assertEqual((p["money"]["spent_stars"], p["money"]["purchases"]), (50, 1))
        self.assertEqual(p["tokens"]["bought"], 10)
        self.assertEqual(p["generations"]["success"], 1)
        texts = [t["text"] for t in p["timeline"]]
        self.assertIn("Регистрация в Nolla AI", texts)
        self.assertIn("Первая генерация", texts)
        self.assertTrue(any(t.startswith("Покупка токенов") for t in texts))
        self.assertEqual(len(p["orders"]), 1)
        with self.assertRaises(DomainError):
            admin_users.user_profile(self.db, 12345, 0.013)

    def test_actions_need_confirmation_and_are_audited(self):
        with self.assertRaises(DomainError) as cm:
            admin_users.act(self.db, self.ADMIN, 1, "credits_add", amount=500)
        self.assertEqual(cm.exception.code, "confirm_required")
        self.assertEqual(credits.get_balance(self.db, 1), 0)
        res = admin_users.act(self.db, self.ADMIN, 1, "credits_add", amount=500, note="подарок", confirm=True)
        self.assertEqual((res["before"]["баланс"], res["after"]["баланс"]), (0, 500))
        admin_users.act(self.db, self.ADMIN, 1, "credits_sub", amount=200, confirm=True)
        self.assertEqual(credits.get_balance(self.db, 1), 300)
        with self.assertRaises(InsufficientCredits):
            admin_users.act(self.db, self.ADMIN, 1, "credits_sub", amount=9999, confirm=True)
        self.assertTrue(self.balance_matches_ledger())
        log = admin_users.audit_list(self.db)
        self.assertEqual(log["total"], 2)
        self.assertIn("@boss", log["items"][0]["admin_name"])
        self.assertEqual(log["items"][1]["after"]["баланс"], 500)

    def test_reset_free_gives_new_free_attempt_and_keeps_history(self):
        o, _ = free(self, "a", prompt="x")
        self.assertFalse(orders.free_status(self.db, 1)["photo"])
        admin_users.act(self.db, self.ADMIN, 1, "reset_free", confirm=True)
        self.assertTrue(orders.free_status(self.db, 1)["photo"])
        o2, _ = free(self, "b", prompt="y")
        self.assertEqual(o2["used_free"], 1)
        self.assertEqual(len(orders.list_user_orders(self.db, 1)), 2)

    def test_invalid_amounts_rejected(self):
        for bad in (0, -5, None, "10"):
            with self.assertRaises(DomainError):
                admin_users.act(self.db, self.ADMIN, 1, "credits_add", amount=bad, confirm=True)
        with self.assertRaises(DomainError):
            admin_users.act(self.db, self.ADMIN, 1, "drop_table", confirm=True)


class ListsAndExportTest(BaseTest):
    def test_generations_filters_and_pagination(self):
        self.add_balance(1, 50)
        for i in range(3):
            o, _ = free(self, f"p{i}", prompt=f"фото {i}")
            generation.process_order(self.db, self.storage, self.mock, o["id"])
        o, _ = free(self, "v", kind="video", prompt="видео")
        generation.process_order(self.db, self.storage, self.live, o["id"])
        self.assertEqual(admin_lists.generations_list(self.db)["total"], 4)
        self.assertEqual(admin_lists.generations_list(self.db, kind="video")["total"], 1)
        self.assertEqual(admin_lists.generations_list(self.db, status="failed")["total"], 1)
        self.assertEqual(len(admin_lists.generations_list(self.db, size=2)["items"]), 2)
        self.assertEqual(admin_lists.generations_list(self.db, q="видео")["total"], 1)
        with self.assertRaises(DomainError):
            admin_lists.generations_list(self.db, status="bogus")

    def test_errors_report_counts_real_errors(self):
        o, _ = free(self, "v", kind="video", prompt="x")
        generation.process_order(self.db, self.storage, self.live, o["id"])
        r = admin_lists.errors_report(self.db)
        self.assertEqual(r["stats"]["today"], 1)
        self.assertEqual(r["stats"]["rate_24h"], 100.0)
        self.assertEqual(r["items"][0]["error_type"], "provider_not_configured")
        self.assertEqual(r["items"][0]["severity"], "warning")

    def test_activity_feed_is_built_from_real_events(self):
        buy(self)
        o, _ = free(self, "a", prompt="x")
        generation.process_order(self.db, self.storage, self.mock, o["id"])
        kinds = {i["type"] for i in admin_lists.activity_feed(self.db)}
        self.assertTrue({"registration", "purchase", "photo"} <= kinds)
        self.assertEqual(admin_lists.activity_feed(self.db, kinds={"purchase"})[0]["amount"], 10)

    def test_referrals_and_marketing(self):
        users.upsert_user(self.db, 20, "inv", "Гость", start_param="ref_1")
        users.upsert_user(self.db, 21, "tt", "Гость2", start_param="src_tiktok_spring")
        users.register(self.db, 20)
        r = admin_lists.referrals(self.db, "nolla_bot")
        self.assertEqual(r["totals"]["invited"], 1)
        self.assertIn("start=ref_1", r["items"][0]["link"])
        m = admin_lists.marketing(self.db)
        labels = {x["source_label"] for x in m["items"]}
        self.assertTrue({"Реферальная ссылка", "TikTok", "Не определён"} <= labels)

    def test_exports_are_csv_with_russian_headers(self):
        buy(self)
        for kind in exports.KINDS:
            name, data = exports.build(self.db, kind, 0.013, "bot")
            self.assertTrue(name.endswith(".csv"))
            self.assertTrue(data.startswith("\ufeff".encode("utf-8")))
        _, data = exports.build(self.db, "users", 0.013)
        self.assertIn("Баланс, токенов", data.decode("utf-8-sig"))
        with self.assertRaises(DomainError):
            exports.build(self.db, "secrets", 0.013)


class ContentTest(BaseTest):
    def test_defaults_then_edit_blocks_and_faq(self):
        c = content.get_all(self.db)
        self.assertEqual(c["hero"]["title"], "Создавай реальность без границ")
        content.update(self.db, "hero", {"title": "Новый заголовок", "text": "t", "primary": "a", "secondary": "b"})
        content.update(self.db, "why", [{"title": "Первое", "text": "x"}, {"title": "", "text": "пусто — отбросится"}])
        c = content.get_all(self.db)
        self.assertEqual(c["hero"]["title"], "Новый заголовок")
        self.assertEqual(len(c["why"]), 1)
        with self.assertRaises(DomainError):
            content.update(self.db, "unknown", {})
        f = content.faq_save(self.db, {"question": "Вопрос?", "answer": "Ответ."})
        self.assertIn("Вопрос?", [x["question"] for x in content.faq_public(self.db)])
        content.faq_save(self.db, {"is_active": False}, f["id"])
        self.assertNotIn("Вопрос?", [x["question"] for x in content.faq_public(self.db)])
        content.faq_delete(self.db, f["id"])
        with self.assertRaises(DomainError):
            content.faq_save(self.db, {"question": "", "answer": ""})

    def test_seeded_faq_models_methods_exist(self):
        self.assertGreaterEqual(len(content.faq_public(self.db)), 8)
        self.assertEqual(len(models.public_list(self.db)), 26)  # 12 изображений + 13 видео + аудио; прежние три модели скрыты
        codes = [m["code"] for m in methods.admin_list(self.db, __import__("app.config", fromlist=["Settings"]).Settings(), False)]
        self.assertEqual(set(codes), {"stars", "sbp", "card", "test"})
