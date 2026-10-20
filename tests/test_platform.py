"""Платформа: аудио, каталоги, инструменты (раскадровка, ракурсы, примерка), аватары, настройки, MCP, демо-оплата, поиск."""
import asyncio
import io
import json
import os
import sqlite3
import tempfile
import unittest

from PIL import Image

from app import mcp
from app.ai.registry import ProviderRegistry
from app.context import AppContext
from app.config import Settings
from app.db import SCHEMA, Database, init_db
from app.errors import DomainError, DuplicateOperation
from app.security import AdminAccess
from app.services import analytics, api_tokens, avatars, catalog, credits, frames, generation, models, orders, params, payments, prefs
from tests.helpers import BaseTest, make_photo


def model_id(test, name):
    with test.db.read() as c:
        return c.execute("SELECT id FROM ai_models WHERE name = ?", (name,)).fetchone()["id"]


def item(test, slug):
    return catalog.get_by_slug(test.db, slug)


def make(test, rid, *, kind="photo", user_id=1, **kw):
    return orders.submit_generation(test.db, test.storage, user_id=user_id, request_id=rid, source="app", kind=kind, **kw)


def run(test, order):
    return generation.process_order(test.db, test.storage, test.mock, order["id"])


class MigrationTest(unittest.TestCase):
    def test_old_database_gets_audio_and_keeps_data(self):
        with tempfile.TemporaryDirectory() as d:
            path = f"{d}/old.db"
            conn = sqlite3.connect(path)
            conn.executescript(SCHEMA.replace("'photo', 'video', 'audio'", "'photo', 'video'"))
            conn.execute("INSERT INTO users (tg_id, username, first_name, balance, created_at) VALUES (7, 'a', 'A', 5, '2026-01-01')")
            conn.execute("INSERT INTO templates (slug, title, kind, created_at, updated_at) VALUES ('old-t', 'Старый', 'photo', 'x', 'x')")
            conn.execute("INSERT INTO orders (user_id, template_id, kind, status, request_id, created_at) VALUES (7, 1, 'photo', 'done', 'r', 'x')")
            conn.execute("INSERT INTO credit_ledger (user_id, delta, reason, order_id, created_at) VALUES (7, -1, 'order_charge', 1, 'x')")
            conn.commit()
            conn.close()
            db = Database(path)
            init_db(db)
            init_db(db)  # повторный запуск безопасен
            with db.tx() as c:
                c.execute("INSERT INTO orders (user_id, template_id, kind, status, request_id, created_at) VALUES (7, 1, 'audio', 'created', 'r2', 'x')")
                self.assertEqual(c.execute("SELECT COUNT(*) FROM orders").fetchone()[0], 2)
                self.assertEqual(c.execute("SELECT COUNT(*) FROM credit_ledger").fetchone()[0], 1)
                self.assertEqual(c.execute("PRAGMA foreign_key_check").fetchall(), [])
                self.assertIn("one_free_per_kind", [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type = 'index'")])
            with self.assertRaises(sqlite3.IntegrityError), db.tx() as c:
                c.execute("INSERT INTO orders (user_id, template_id, kind, status, request_id, created_at) VALUES (7, 1, 'text', 'created', 'r3', 'x')")


class SeedTest(BaseTest):
    def test_models_follow_the_brief(self):
        names = {k: [m["name"] for m in models.public_list(self.db, k)] for k in ("photo", "video", "audio")}
        self.assertEqual(len(names["photo"]), 12)
        self.assertEqual(len(names["video"]), 13)
        self.assertEqual(names["audio"], ["Eleven"])
        for n in ("Nano Banana", "Nano Banana Pro", "Nano Banana 2", "Nano Banana 2 Lite", "Nano Banana 2.1", "Seedream 5 Pro", "Grok Image 2",
                  "Wan 2.7 Pro", "Midjourney", "FLUX.2 Flex", "Lexy Aura", "GPT Image 2.5"):
            self.assertIn(n, names["photo"])
        for n in ("Seedance 2.5", "Seedance 2.0", "Kling 3.0 Photo", "Kling 3.0 Motion Control", "Kling 3.0 Frames", "Kling 3.0 Text", "Grok Imagine 1.5",
                  "Veo Omni Flash", "Veo 3.1", "Happy Horse 1.1", "Higgsfield Genjutsu", "Topaz Upscale", "Wan 3.0"):
            self.assertIn(n, names["video"])
        self.assertTrue(models.public_list(self.db, "photo", "photoreal"))
        self.assertTrue(models.public_list(self.db, "video", "upscale"))

    def test_sections_are_filled_and_russian(self):
        self.assertEqual(len(catalog.list_items(self.db, "effect")), 16)
        self.assertEqual(len(catalog.list_items(self.db, "photoshoot", "luxury")), 2)
        self.assertEqual(len(catalog.list_items(self.db, "marketing")), 10)
        self.assertEqual(len(catalog.list_items(self.db, "mtool")), 10)
        m = catalog.meta(self.db)
        self.assertEqual(len(m["sections"]["prompt"]["tags"]), 13)
        self.assertEqual(len(m["sections"]["photoshoot"]["tags"]), 13)
        self.assertTrue(all(t["count"] > 0 for t in m["sections"]["prompt"]["tags"]))
        self.assertTrue(all(t["count"] > 0 for t in m["sections"]["trend"]["tags"]))
        self.assertTrue(catalog.list_items(self.db, "trend", "popular"))
        p = catalog.list_items(self.db, "prompt")[0]
        self.assertGreater(p["price_credits"], 0)
        self.assertIn("Nano Banana 2", p["supported_models"])
        self.assertEqual(len(m["quick_actions"]), 8)

    def test_packages_are_demo_priced_and_old_ones_hidden(self):
        with self.db.read() as c:
            ids = [r["id"] for r in c.execute("SELECT id FROM packages WHERE is_active = 1 AND id IN ('start', 'pro', 'creator', 'studio') ORDER BY sort_order")]
        self.assertEqual(ids, ["start", "pro", "creator", "studio"])


class AudioTest(BaseTest):
    def test_audio_order_costs_tokens_makes_wav_and_has_no_free_attempt(self):
        self.add_balance(1, 50)
        o, _ = make(self, "a1", kind="audio", prompt="Привет! Проверка озвучки.", params={"voice": "alina", "emotion": "joy", "speed": 1.2},
                    model_id=model_id(self, "Eleven"))
        self.assertEqual((o["used_free"], o["price_credits"], o["kind"]), (0, 10, "audio"))
        done = run(self, o)
        self.assertEqual((done["status"], done["result_mime"]), ("done", "audio/wav"))
        self.assertTrue(done["is_stub"])
        with open(done["result_path"], "rb") as f:
            self.assertEqual(f.read(4), b"RIFF")
        self.assertGreaterEqual(done["duration_sec"], 1)
        self.assertEqual(credits.get_balance(self.db, 1), 40)
        self.assertTrue(self.balance_matches_ledger())
        self.assertEqual(orders.free_status(self.db, 1), {"photo": True, "video": True})

    def test_audio_needs_text_and_rejects_files(self):
        self.add_balance(1, 50)
        with self.assertRaises(DomainError):
            make(self, "a", kind="audio", prompt="  ")
        with self.assertRaises(DomainError) as e:
            make(self, "b", kind="audio", prompt="текст", image_bytes=make_photo())
        self.assertEqual(e.exception.code, "unsupported_input")
        self.assertEqual(orders.list_user_orders(self.db, 1), [])

    def test_audio_text_up_to_2000_but_images_only_500(self):
        self.add_balance(1, 50)
        make(self, "ok", kind="audio", prompt="слово " * 300)
        with self.assertRaises(DomainError):
            make(self, "bad", kind="audio", prompt="я" * 2001)
        with self.assertRaises(DomainError):
            make(self, "bad2", kind="photo", prompt="я" * 501)

    def test_failed_audio_refunds_tokens(self):
        self.add_balance(1, 20)
        o, _ = make(self, "a", kind="audio", prompt="текст")
        generation.process_order(self.db, self.storage, self.live, o["id"])  # провайдер не подключён
        self.assertEqual(credits.get_balance(self.db, 1), 20)
        self.assertEqual(orders.get_order(self.db, o["id"])["status"], "failed")

    def test_params_validation(self):
        self.assertEqual(params.clean_params({"seed": "42", "speed": "1.5", "duration": 10, "resolution": "2k", "voice": "maxim"}),
                         {"resolution": "2k", "duration": "10", "voice": "maxim", "seed": 42, "speed": 1.5})
        for bad in ({"seed": -1}, {"speed": 3}, {"voice": "x"}, {"resolution": "8k"}, {"emotion": "rage"}):
            with self.assertRaises(DomainError):
                params.clean_params(bad)


class ModelInputTest(BaseTest):
    def test_text_only_and_image_only_models(self):
        self.add_balance(1, 500)
        with self.assertRaises(DomainError) as e:
            make(self, "a", kind="video", prompt="x", image_bytes=make_photo(), model_id=model_id(self, "Kling 3.0 Text"))
        self.assertEqual(e.exception.code, "unsupported_input")
        with self.assertRaises(DomainError) as e:
            make(self, "b", kind="video", prompt="x", model_id=model_id(self, "Kling 3.0 Photo"))
        self.assertEqual(e.exception.code, "photo_required")
        o, _ = make(self, "c", kind="video", prompt="x", image_bytes=make_photo(), model_id=model_id(self, "Kling 3.0 Photo"))
        self.assertEqual(o["price_credits"], 0 if o["used_free"] else 70)
        o2, _ = make(self, "d", kind="video", prompt="x", model_id=model_id(self, "Kling 3.0 Text"))
        self.assertEqual(o2["price_credits"], 70)
        self.assertTrue(self.balance_matches_ledger())

    def test_wrong_kind_model_rejected(self):
        with self.assertRaises(DomainError):
            make(self, "a", kind="photo", prompt="x", model_id=model_id(self, "Veo 3.1"))


class ToolsTest(BaseTest):
    def test_storyboard_makes_nine_frames_and_a_sheet(self):
        self.add_balance(1, 200)
        fx = item(self, "fx-storyboard")
        o, _ = make(self, "s", template_id=fx["id"], image_bytes=make_photo())
        self.assertEqual(o["price_credits"], 0 if o["used_free"] else 40)
        done = run(self, o)
        pub = orders.public_order(orders.get_user_order(self.db, 1, done["id"]))
        self.assertEqual(len(pub["frames"]), 9)
        self.assertEqual(pub["frames"][0], "1 · Общий план")
        self.assertEqual(pub["frames"][8], "9 · Финальный кадр")
        self.assertEqual(pub["group"], "effects")
        for i in range(9):
            self.assertTrue(os.path.exists(orders.frame_path(orders.get_user_order(self.db, 1, done["id"]), i)))
        self.assertIsNone(orders.frame_path(orders.get_user_order(self.db, 1, done["id"]), 9))

    def test_storyboard_works_from_idea_without_photo_but_needs_one_of_them(self):
        self.add_balance(1, 200)
        fx = item(self, "fx-storyboard")
        with self.assertRaises(DomainError):
            make(self, "a", template_id=fx["id"])
        o, _ = make(self, "b", template_id=fx["id"], prompt="Космонавт находит старый маяк")
        self.assertEqual(len(orders.public_order(orders.get_user_order(self.db, 1, run(self, o)["id"]))["frames"]), 9)

    def test_nine_angles(self):
        self.add_balance(1, 200)
        o, _ = make(self, "a", template_id=item(self, "fx-angles")["id"], image_bytes=make_photo())
        pub = orders.public_order(orders.get_user_order(self.db, 1, run(self, o)["id"]))
        self.assertEqual([f.split(" · ")[1] for f in pub["frames"]][:3], ["Спереди", "Слева", "Справа"])
        self.assertEqual(len(pub["frames"]), 9)
        with self.assertRaises(DomainError):
            make(self, "b", template_id=item(self, "fx-angles")["id"])

    def test_tryon_needs_both_images_and_deletes_both_after(self):
        self.add_balance(1, 100)
        fx = item(self, "fx-tryon")
        with self.assertRaises(DomainError) as e:
            make(self, "a", template_id=fx["id"], image_bytes=make_photo())
        self.assertEqual(e.exception.code, "garment_required")
        with self.assertRaises(DomainError):
            make(self, "b", template_id=fx["id"], image2_bytes=make_photo())
        o, _ = make(self, "c", template_id=fx["id"], image_bytes=make_photo(), image2_bytes=make_photo())
        p1, p2 = o["input_path"], o["input2_path"]
        self.assertTrue(os.path.exists(p1) and os.path.exists(p2))
        run(self, o)
        self.assertFalse(os.path.exists(p1) or os.path.exists(p2))

    def test_regen_frame_charges_once_per_request_and_refunds_on_failure(self):
        self.add_balance(1, 200)
        o, _ = make(self, "s", template_id=item(self, "fx-storyboard")["id"], image_bytes=make_photo())
        run(self, o)
        before = credits.get_balance(self.db, 1)
        res = frames.regen_frame(self.db, self.storage, self.mock, user_id=1, order_id=o["id"], index=3, request_id="rq1")
        self.assertEqual(len(res["frames"]), 9)
        self.assertEqual(credits.get_balance(self.db, 1), before - 4)
        frames.regen_frame(self.db, self.storage, self.mock, user_id=1, order_id=o["id"], index=3, request_id="rq1")  # повтор
        self.assertEqual(credits.get_balance(self.db, 1), before - 4)
        with self.assertRaises(DomainError):
            frames.regen_frame(self.db, self.storage, self.live, user_id=1, order_id=o["id"], index=1, request_id="rq2")
        self.assertEqual(credits.get_balance(self.db, 1), before - 4)  # возврат
        with self.assertRaises(DomainError):
            frames.regen_frame(self.db, self.storage, self.mock, user_id=1, order_id=o["id"], index=9, request_id="rq3")
        self.assertTrue(self.balance_matches_ledger())

    def test_marketing_tool_uses_its_default_format(self):
        self.add_balance(1, 100)
        t = item(self, "mt-product-photo")
        o, _ = make(self, "m", template_id=t["id"], image_bytes=make_photo())
        done = run(self, o)
        with Image.open(done["result_path"]) as im:
            self.assertEqual(im.size[0], im.size[1])  # 1:1

    def test_history_groups(self):
        self.add_balance(1, 300)
        a, _ = make(self, "a", prompt="кот")
        b, _ = make(self, "b", kind="video", prompt="кот")
        c, _ = make(self, "c", kind="audio", prompt="текст")
        d, _ = make(self, "d", template_id=item(self, "fx-enhance")["id"], image_bytes=make_photo())
        e, _ = make(self, "e", template_id=item(self, "mk-city")["id"], image_bytes=make_photo())
        groups = {o["id"]: orders.public_order(o)["group"] for o in orders.list_user_orders(self.db, 1)}
        self.assertEqual([groups[x["id"]] for x in (a, b, c, d, e)], ["images", "video", "audio", "effects", "marketing"])

    def test_stage_is_reported_by_provider_without_percent(self):
        o, _ = make(self, "a", prompt="кот")
        done = run(self, o)
        self.assertEqual(orders.public_order(orders.get_user_order(self.db, 1, done["id"]))["stage"], "almost")
        self.assertNotIn("percent", orders.public_order(orders.get_user_order(self.db, 1, done["id"])))


class ReferenceTest(BaseTest):
    def test_use_own_result_as_reference_only(self):
        self.add_balance(1, 100)
        o, _ = make(self, "a", prompt="кот")
        run(self, o)
        o2, _ = make(self, "b", prompt="сделай ярче", ref_order_id=o["id"])
        self.assertIsNotNone(o2["input_path"])
        from app.services import users
        users.upsert_user(self.db, 2, "b", "Б")
        users.register(self.db, 2)
        self.add_balance(2, 100)
        with self.assertRaises(DomainError):
            make(self, "c", prompt="чужое", ref_order_id=o["id"], user_id=2)

    def test_video_result_cannot_be_reference(self):
        self.add_balance(1, 100)
        v, _ = make(self, "v", kind="video", prompt="кот")
        run(self, v)
        with self.assertRaises(DomainError):
            make(self, "x", prompt="y", ref_order_id=v["id"])


class AvatarTest(BaseTest):
    def photos(self, n=3):
        return [make_photo((300 + i, 300)) for i in range(n)]

    def create(self, **kw):
        args = dict(name="Я", photos=self.photos(), consent=True, max_bytes=10 * 1024 * 1024)
        args.update(kw)
        return avatars.create(self.db, self.storage, 1, args["name"], args["photos"], args["consent"], args["max_bytes"])

    def test_consent_and_photo_count(self):
        with self.assertRaises(DomainError) as e:
            self.create(consent=False)
        self.assertEqual(e.exception.code, "consent_required")
        with self.assertRaises(DomainError):
            self.create(photos=self.photos(2))
        with self.assertRaises(DomainError):
            self.create(photos=self.photos(26))
        with self.assertRaises(DomainError):
            self.create(photos=[b"not an image"] * 3)
        self.assertEqual(avatars.list_for_user(self.db, 1), [])
        self.assertEqual(os.listdir(self.storage.root / "avatars") if (self.storage.root / "avatars").exists() else [], [])

    def test_lifecycle_demo_scene_and_delete(self):
        a = self.create()
        self.assertEqual(a["status"], "queued")
        avatars.process(self.db, self.storage, "mock", a["id"])
        pub = avatars.get_owned(self.db, 1, a["id"])
        self.assertEqual(pub["status"], "ready")
        self.assertTrue(avatars.public(pub)["is_stub"])
        self.add_balance(1, 100)
        scene = catalog.list_items(self.db, "avatar", "travel")[0]
        self.assertTrue(scene["needs_avatar"])
        with self.assertRaises(DomainError):
            make(self, "x", template_id=scene["id"])  # аватар не выбран
        o, _ = make(self, "y", template_id=scene["id"], avatar_id=a["id"])
        self.assertEqual(o["avatar_id"], a["id"])
        self.assertEqual(run(self, o)["status"], "done")
        avatars.delete(self.db, self.storage, 1, a["id"])
        self.assertEqual(os.listdir(self.storage.root / "avatars"), [])
        with self.assertRaises(DomainError):
            make(self, "z", template_id=scene["id"], avatar_id=a["id"])

    def test_live_mode_without_provider_fails_honestly_and_not_ready_avatar_is_rejected(self):
        a = self.create()
        self.add_balance(1, 100)
        scene = catalog.list_items(self.db, "avatar")[0]
        with self.assertRaises(DomainError):
            make(self, "q", template_id=scene["id"], avatar_id=a["id"])  # ещё не готов
        avatars.process(self.db, self.storage, "live", a["id"])
        got = avatars.get_owned(self.db, 1, a["id"])
        self.assertEqual(got["status"], "failed")
        self.assertIn("не подключено", got["error"])

    def test_other_user_cannot_see_or_use_avatar(self):
        from app.services import users
        a = self.create()
        avatars.process(self.db, self.storage, "mock", a["id"])
        users.upsert_user(self.db, 2, "b", "Б")
        users.register(self.db, 2)
        self.add_balance(2, 100)
        with self.assertRaises(DomainError):
            avatars.get_owned(self.db, 2, a["id"])
        with self.assertRaises(DomainError):
            make(self, "w", template_id=catalog.list_items(self.db, "avatar")[0]["id"], avatar_id=a["id"], user_id=2)

    def test_limit_and_restart_recovery(self):
        for _ in range(5):
            self.create()
        with self.assertRaises(DomainError) as e:
            self.create()
        self.assertEqual(e.exception.code, "avatar_limit")
        self.assertEqual(avatars.fail_unfinished(self.db), 5)
        self.assertEqual(avatars.delete_all(self.db, self.storage, 1), 5)
        self.assertEqual(os.listdir(self.storage.root / "avatars"), [])


class PrefsTest(BaseTest):
    def test_defaults_update_and_validation(self):
        self.assertEqual(prefs.get(self.db, 1)["ratio"], "1:1")
        got = prefs.update(self.db, 1, {"ratio": "9:16", "quality": "high", "autodownload": True, "notify": False, "interests": ["photo", "ads"],
                                        "default_model_id": model_id(self, "Midjourney")})
        self.assertEqual((got["ratio"], got["quality"], got["autodownload"], got["notify"]), ("9:16", "high", True, False))
        self.assertEqual(got["interests"], ["photo", "ads"])
        with self.assertRaises(DomainError):
            prefs.update(self.db, 1, {"ratio": "5:7"})
        with self.assertRaises(DomainError):
            prefs.update(self.db, 1, {"default_model_id": model_id(self, "Veo 3.1")})  # видеомодель по умолчанию для изображений
        with self.assertRaises(DomainError):
            prefs.update(self.db, 1, {"interests": ["x"]})
        self.assertEqual(prefs.update(self.db, 1, {"default_model_id": None})["default_model_id"], None)
        self.assertEqual(prefs.get(self.db, 1)["ratio"], "9:16")


class DemoPaymentTest(BaseTest):
    def test_demo_payment_credits_tokens_but_is_not_revenue(self):
        before = credits.get_balance(self.db, 1)
        pay, credited = payments.demo_payment(self.db, 1, "pro", "sbp")
        self.assertTrue(credited)
        self.assertEqual(credits.get_balance(self.db, 1), before + 1500 + 100)
        self.assertEqual(pay["provider"], "test")
        self.assertEqual(payments.list_user_payments(self.db, 1)[0]["demo_method"], "sbp")
        from datetime import date, timedelta
        rep = analytics.overview(self.db, date.today() - timedelta(days=1), date.today(), 0.013)
        self.assertEqual(json.dumps(rep, default=str).count("1290"), 0)  # демо-цена не попадает в выручку
        self.assertTrue(self.balance_matches_ledger())

    def test_unknown_method_and_package_rejected(self):
        with self.assertRaises(DomainError):
            payments.demo_payment(self.db, 1, "pro", "paypal")
        with self.assertRaises(DomainError):
            payments.demo_payment(self.db, 1, "nope", "card")


class SearchTest(BaseTest):
    def test_search_groups(self):
        self.add_balance(1, 50)
        make(self, "a", prompt="серебряный дракон над морем")
        groups = {g["type"]: g for g in catalog.search(self.db, 1, "дракон")}
        self.assertIn("history", groups)
        self.assertEqual({g["type"] for g in catalog.search(self.db, 1, "kling")}, {"model"})
        self.assertIn("effect", {g["type"] for g in catalog.search(self.db, 1, "Раскадровка")})
        self.assertIn("prompt", {g["type"] for g in catalog.search(self.db, 1, "нуар")})
        self.assertEqual(catalog.search(self.db, 1, "я"), [])  # слишком короткий запрос
        self.assertEqual(catalog.search(self.db, 2, "дракон"), [])  # чужая история не видна


class McpTest(BaseTest):
    def setUp(self):
        super().setUp()
        outer = self

        class Runner:
            def __init__(self):
                self.scheduled = []
                self.notifier = None

            def schedule(self, order_id):
                self.scheduled.append(order_id)

        settings = Settings(webapp_url="https://app.example")
        self.ctx = AppContext(settings, self.db, self.storage, self.mock, Runner(), AdminAccess(frozenset(), frozenset()))
        del outer

    def call(self, method, params=None, uid=1, id_=1):
        return asyncio.run(mcp.handle(self.ctx, uid, {"jsonrpc": "2.0", "id": id_, "method": method, "params": params or {}}))

    def tool(self, name, args=None, uid=1):
        res = self.call("tools/call", {"name": name, "arguments": args or {}}, uid)["result"]
        return res["isError"], json.loads(res["content"][0]["text"]) if not res["isError"] else res["content"][0]["text"]

    def test_protocol_basics(self):
        self.assertEqual(self.call("initialize")["result"]["serverInfo"]["name"], "nolla-ai")
        self.assertEqual(len(self.call("tools/list")["result"]["tools"]), 7)
        self.assertIsNone(asyncio.run(mcp.handle(self.ctx, 1, {"jsonrpc": "2.0", "method": "notifications/initialized"})))
        self.assertEqual(self.call("nope")["error"]["code"], -32601)
        self.assertEqual(self.call("tools/call", {"name": "hack"})["error"]["code"], -32602)

    def test_create_status_balance_history_and_reference_edit(self):
        self.add_balance(1, 100)
        err, out = self.tool("create_image", {"prompt": "кот в космосе", "model": "Nano Banana 2", "format": "3:4", "request_id": "r1"})
        self.assertFalse(err)
        self.assertEqual((out["status"], out["kind"]), ("queued", "image" if False else "photo"))
        self.assertEqual(self.ctx.runner.scheduled, [out["order_id"]])
        _, again = self.tool("create_image", {"prompt": "кот в космосе", "request_id": "r1"})
        self.assertEqual(again["order_id"], out["order_id"])
        self.assertEqual(len(self.ctx.runner.scheduled), 1)  # повтор ничего не запускает
        generation.process_order(self.db, self.storage, self.mock, out["order_id"])
        _, st = self.tool("get_generation_status", {"order_id": out["order_id"]})
        self.assertEqual(st["status"], "done")
        self.assertTrue(st["result_url"].startswith("https://app.example/mcp/result/"))
        self.assertTrue(st["demo_result"])
        err, edit = self.tool("edit_image", {"order_id": out["order_id"], "prompt": "добавь луну"})
        self.assertFalse(err)
        _, bal = self.tool("get_balance")
        self.assertEqual(bal["balance"], credits.get_balance(self.db, 1))
        _, hist = self.tool("get_history", {"limit": 5})
        self.assertEqual(len(hist["items"]), 2)
        self.assertTrue(self.balance_matches_ledger())

    def test_audio_video_errors_and_isolation(self):
        self.add_balance(1, 100)
        err, text = self.tool("create_audio", {"text": ""})
        self.assertTrue(err)
        err, out = self.tool("create_audio", {"text": "Привет", "voice": "igor", "speed": 1.1})
        self.assertFalse(err)
        self.assertEqual(out["kind"], "audio")
        err, text = self.tool("create_video", {"prompt": "x", "model": "Не существует"})
        self.assertTrue(err)
        from app.services import users
        users.upsert_user(self.db, 2, "b", "Б")
        users.register(self.db, 2)
        err, text = self.tool("get_generation_status", {"order_id": out["order_id"]}, uid=2)
        self.assertTrue(err)  # чужую генерацию не видно
        err, text = self.tool("edit_image", {"prompt": "x"})
        self.assertTrue(err)  # не хватает аргумента


class TokensTest(BaseTest):
    def test_token_is_shown_once_stored_hashed_and_revocable(self):
        t = api_tokens.create(self.db, 1, "Cursor")
        self.assertTrue(t["token"].startswith("nolla_"))
        with self.db.read() as c:
            dump = json.dumps([tuple(r) for r in c.execute("SELECT * FROM api_tokens")])
        self.assertNotIn(t["token"], dump)
        self.assertEqual(api_tokens.authenticate(self.db, t["token"]), 1)
        self.assertIsNone(api_tokens.authenticate(self.db, "nolla_wrong"))
        self.assertIsNone(api_tokens.authenticate(self.db, "other"))
        self.assertEqual(len(api_tokens.list_for_user(self.db, 1)), 1)
        self.assertNotIn("token", api_tokens.list_for_user(self.db, 1)[0])
        api_tokens.revoke(self.db, 1, t["id"])
        self.assertIsNone(api_tokens.authenticate(self.db, t["token"]))
        with self.assertRaises(DomainError):
            api_tokens.revoke(self.db, 2, t["id"])

    def test_limit_and_blocked_user(self):
        toks = [api_tokens.create(self.db, 1) for _ in range(5)]
        with self.assertRaises(DomainError):
            api_tokens.create(self.db, 1)
        with self.db.tx() as c:
            c.execute("UPDATE users SET status = 'blocked' WHERE tg_id = 1")
        self.assertIsNone(api_tokens.authenticate(self.db, toks[0]["token"]))


class MediaCleanupTest(BaseTest):
    def test_delete_my_media_removes_frames_and_second_images(self):
        self.add_balance(1, 200)
        o, _ = make(self, "s", template_id=item(self, "fx-storyboard")["id"], image_bytes=make_photo())
        run(self, o)
        paths = [orders.frame_path(orders.get_user_order(self.db, 1, o["id"]), i) for i in range(9)]
        orders.delete_user_media(self.db, self.storage, 1)
        self.assertFalse(any(os.path.exists(p) for p in paths))
        o2, _ = make(self, "t", template_id=item(self, "fx-angles")["id"], image_bytes=make_photo())
        run(self, o2)
        paths2 = [orders.frame_path(orders.get_user_order(self.db, 1, o2["id"]), i) for i in range(9)]
        orders.delete_order(self.db, self.storage, 1, o2["id"])
        self.assertFalse(any(os.path.exists(p) for p in paths2))


if __name__ == "__main__":
    unittest.main()


class AdminFieldsTest(BaseTest):
    def test_admin_can_create_platform_template_and_audio_kind(self):
        from app.services import templates
        t = templates.create(self.db, {"title": "Новый эффект", "kind": "photo", "section": "effect", "tag": "edit", "tool": "enhance",
                                       "required": ["photo"], "price_credits": 5, "is_published": True})
        got = catalog.get_item(self.db, t["id"])
        self.assertEqual((got["section"], got["tag"], got["price_credits"]), ("effect", "edit", 5))
        self.assertEqual(got["required"], [{"code": "photo", "label": "Фото"}])
        with self.assertRaises(DomainError):
            templates.update(self.db, t["id"], {"section": "nope"})
        with self.assertRaises(DomainError):
            templates.update(self.db, t["id"], {"required": "not-a-list-[["})
        a = templates.create(self.db, {"title": "Озвучка", "kind": "audio"})
        self.assertEqual(a["model"], "audio-default")

    def test_analytics_and_admin_lists_count_audio(self):
        from datetime import date, timedelta
        from app.services import admin_lists
        self.add_balance(1, 100)
        o, _ = make(self, "a", kind="audio", prompt="текст")
        run(self, o)
        rep = analytics.overview(self.db, date.today() - timedelta(days=1), date.today(), 0.013)
        self.assertEqual(rep["generations"]["audio"], 1)
        got = admin_lists.generations_list(self.db, kind="audio")
        self.assertEqual(len(got["items"]), 1)


class PreviewPhotosTest(BaseTest):
    def test_upload_list_and_delete(self):
        from app.services import previews
        self.assertEqual(previews.list_public(self.storage), [])
        a = previews.save(self.storage, make_photo((900, 1600)), 10 * 1024 * 1024)
        previews.save(self.storage, make_photo((600, 1000)), 10 * 1024 * 1024)
        urls = previews.list_public(self.storage)
        self.assertEqual(len(urls), 2)
        self.assertTrue(all(u.startswith("/media/previews/") for u in urls))
        self.assertEqual(len(previews.list_admin(self.storage)), 2)
        with self.assertRaises(DomainError):
            previews.save(self.storage, b"not an image", 10 * 1024 * 1024)
        with self.assertRaises(DomainError):
            previews.delete(self.storage, "../../secret.jpg")
        previews.delete(self.storage, a["name"])
        self.assertEqual(len(previews.list_public(self.storage)), 1)


class ShowcaseTest(BaseTest):
    """Витрина: админ наполняет «Идеи» и главную, меняет порядок и видимость."""

    def card(self, **kw):
        from app.services import templates
        base = {"title": "Идея", "kind": "photo", "section": "idea", "tag": "portrait", "price_credits": 12, "is_published": True}
        base.update(kw)
        return templates.create(self.db, base)

    def test_ideas_flags_order_and_featured(self):
        from app.services import templates
        a = self.card(title="Первая", sort_order=20)
        b = self.card(title="Вторая", sort_order=10)
        c = self.card(title="Рекомендованная", sort_order=30, is_popular=True)
        self.assertEqual([i["title"] for i in catalog.list_items(self.db, "idea")], ["Рекомендованная", "Вторая", "Первая"])
        self.assertTrue(catalog.list_items(self.db, "idea")[0]["featured"])
        templates.update(self.db, c["id"], {"on_ideas": False})
        self.assertEqual([i["title"] for i in catalog.list_items(self.db, "idea", on_ideas=True)], ["Вторая", "Первая"])
        templates.update(self.db, b["id"], {"on_home": False})
        self.assertEqual([i["title"] for i in catalog.list_items(self.db, "idea", on_home=True)], ["Рекомендованная", "Первая"])
        templates.update(self.db, a["id"], {"is_published": False})
        self.assertNotIn("Первая", [i["title"] for i in catalog.list_items(self.db, "idea")])

    def test_move_and_duplicate(self):
        from app.services import templates
        a = self.card(title="А", sort_order=10)
        b = self.card(title="Б", sort_order=20)
        self.assertEqual(templates.move(self.db, b["id"], "down"), {"moved": False})
        self.assertEqual(templates.move(self.db, b["id"], "up"), {"moved": True})
        self.assertEqual([i["title"] for i in catalog.list_items(self.db, "idea")], ["Б", "А"])
        copy = templates.duplicate(self.db, a["id"])
        self.assertEqual(copy["title"], "А (копия)")
        self.assertEqual((copy["is_published"], copy["section"], copy["tag"]), (0, "idea", "portrait"))
        self.assertNotEqual(copy["slug"], a["slug"])
        self.assertNotIn("А (копия)", [i["title"] for i in catalog.list_items(self.db, "idea")])  # копия скрыта
        with self.assertRaises(DomainError):
            templates.move(self.db, a["id"], "вбок")

    def test_idea_card_can_be_generated(self):
        self.add_balance(1, 100)
        t = self.card(title="Ночь", prompt="night city portrait")
        o, _ = make(self, "i1", template_id=t["id"])
        self.assertEqual(run(self, o)["status"], "done")


class BotSyncTest(BaseTest):
    """Бот и приложение — одна система: общий пользователь, общая история, общая статистика."""

    def test_bot_orders_counted_separately_and_together(self):
        from datetime import date, timedelta
        from app.services import admin_users
        self.add_balance(1, 300)
        a, _ = orders.submit_generation(self.db, self.storage, user_id=1, request_id="b1", source="bot", kind="photo", prompt="кот")
        run(self, a)
        b, _ = orders.submit_generation(self.db, self.storage, user_id=1, request_id="a1", source="app", kind="audio", prompt="текст")
        run(self, b)
        st = analytics.bot_stats(self.db, date.today() - timedelta(days=1), date.today())
        self.assertEqual((st["generations_total"], st["photo"], st["audio"]), (1, 1, 0))
        self.assertEqual(st["app"]["generations_period"], 1)
        row = admin_users.users_list(self.db)["items"][0]
        self.assertEqual((row["generations"], row["photos"], row["audios"], row["via_bot"]), (2, 1, 1, 1))
        self.assertEqual(len(orders.list_user_orders(self.db, 1)), 2)  # обе работы в «Моих генерациях»
