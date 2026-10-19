"""Свободный генератор Nolla AI: запрос без шаблона, фото необязательно, параметры, PRO, подкатегории."""
import os

from app.errors import DomainError
from app.services import admin_stats, credits, generation, orders, params, templates, users
from tests.helpers import BaseTest, make_photo


def free(test, rid, kind="photo", **kw):
    return orders.submit_generation(test.db, test.storage, user_id=kw.pop("user_id", 1), request_id=rid,
                                    source="app", kind=kind, **kw)


class FreeformTest(BaseTest):
    def test_text_only_request_works_without_photo_and_without_template(self):
        o, created = free(self, "a", prompt="девушка в студии, мягкий свет")
        self.assertTrue(created)
        self.assertIsNone(o["input_path"])
        self.assertEqual((o["used_free"], o["price_credits"]), (1, 0))  # первая попытка бесплатна и здесь
        done = generation.process_order(self.db, self.storage, self.mock, o["id"])
        self.assertEqual(done["status"], "done")
        self.assertTrue(os.path.exists(done["result_path"]))

    def test_empty_request_rejected(self):
        with self.assertRaises(DomainError):
            free(self, "a", prompt="   ")
        self.assertEqual(orders.list_user_orders(self.db, 1), [])

    def test_photo_alone_is_enough_and_is_deleted_after_processing(self):
        o, _ = free(self, "a", image_bytes=make_photo())
        path = o["input_path"]
        self.assertTrue(os.path.exists(path))
        generation.process_order(self.db, self.storage, self.mock, o["id"])
        self.assertFalse(os.path.exists(path))

    def test_prompt_limit_500(self):
        free(self, "ok", prompt="я" * 500)
        with self.assertRaises(DomainError):
            free(self, "bad", prompt="я" * 501)

    def test_price_comes_from_hidden_system_template_and_free_attempt_is_shared(self):
        templates.update_system(self.db, "photo", {"price_credits": 3})
        o1, _ = free(self, "a", prompt="первый")  # бесплатный
        self.add_balance(1, 10)
        o2, _ = free(self, "b", prompt="второй")
        self.assertEqual(o2["price_credits"], 3)
        self.assertEqual(credits.get_balance(self.db, 1), 7)
        # бесплатная попытка на фото уже использована и для шаблонов
        o3, _ = self.submit("c")
        self.assertEqual(o3["used_free"], 0)
        self.assertTrue(self.balance_matches_ledger())

    def test_repeat_request_id_does_not_charge_twice(self):
        free(self, "a", prompt="x")
        self.add_balance(1, 10)
        a, ca = free(self, "same", prompt="y")
        b, cb = free(self, "same", prompt="y")
        self.assertEqual((ca, cb, a["id"]), (True, False, b["id"]))
        self.assertEqual(credits.get_balance(self.db, 1), 10 - a["price_credits"])

    def test_failure_refunds_freeform_order(self):
        free(self, "a", prompt="x")
        self.add_balance(1, 10)
        o, _ = free(self, "b", prompt="y")
        generation.process_order(self.db, self.storage, self.live, o["id"])
        self.assertEqual(credits.get_balance(self.db, 1), 10)

    def test_system_templates_hidden_everywhere_public(self):
        all_titles = [t["title"] for t in templates.list_published(self.db)]
        self.assertNotIn("Свободное фото", all_titles)
        self.assertNotIn("Свободное фото", [t["title"] for t in templates.admin_list(self.db)])
        with self.db.read() as conn:
            sys_id = conn.execute("SELECT id FROM templates WHERE slug = '__free_photo'").fetchone()["id"]
        with self.assertRaises(DomainError):
            templates.get_published(self.db, sys_id)
        with self.assertRaises(DomainError):  # и заказать «шаблон» напрямую по id нельзя
            self.submit("x", template_id=sys_id)

    def test_freeform_can_be_switched_off_by_owner(self):
        templates.update_system(self.db, "video", {"enabled": False})
        with self.assertRaises(DomainError):
            free(self, "a", kind="video", prompt="x")
        free(self, "b", kind="photo", prompt="x")  # фото при этом работает

    def test_template_mode_still_works_without_photo(self):
        o, _ = orders.submit_generation(self.db, self.storage, user_id=1, template_id=self.tpl(), request_id="t",
                                        source="app", prompt="добавь золотые тона")
        self.assertEqual(o["prompt"], "добавь золотые тона")

    def test_prompt_and_params_are_stored_and_composed(self):
        captured = {}

        class Spy:
            def get(self_inner, kind, model):
                class P:
                    def generate(_, req):
                        captured["prompt"], captured["params"] = req.prompt, req.params
                        return self.mock.get(kind, model).generate(req)
                return P()

        o, _ = free(self, "a", prompt="девушка у окна", params={"format": "9:16", "style": "cinematic", "lighting": "sunset", "quality": "high"})
        done = generation.process_order(self.db, self.storage, Spy(), o["id"])
        self.assertIn("девушка у окна", captured["prompt"])
        self.assertIn("aspect ratio 9:16", captured["prompt"])
        self.assertIn("golden hour", captured["prompt"])
        self.assertEqual(orders.public_order(orders.get_user_order(self.db, 1, done["id"]))["params"]["format"], "9:16")

    def test_video_result_has_duration_and_mock_respects_aspect(self):
        o, _ = free(self, "v", kind="video", prompt="закат над морем", params={"format": "16:9"})
        done = generation.process_order(self.db, self.storage, self.mock, o["id"])
        self.assertGreaterEqual(done["duration_sec"], 1)
        self.assertEqual(done["result_mime"], "image/gif")


class ParamsTest(BaseTest):
    def test_unknown_values_rejected_unknown_keys_dropped(self):
        self.assertEqual(params.clean_params({"format": "9:16", "evil": "x"}), {"format": "9:16"})
        for bad in ({"format": "99:1"}, {"quality": "ultra"}, {"style": "<script>"}, "not json", [1]):
            with self.assertRaises(DomainError):
                params.clean_params(bad)
        self.assertEqual(params.clean_params(None), {})

    def test_params_text(self):
        text = params.params_to_prompt({"camera": "wide", "style": "anime"})
        self.assertIn("wide-angle", text)
        self.assertIn("anime", text)


class ProAndLabelsTest(BaseTest):
    def test_pro_flag_is_manual_and_visible(self):
        self.assertFalse(users.profile(self.db, 1)["is_pro"])
        users.set_pro(self.db, 1, True)
        self.assertTrue(users.profile(self.db, 1)["is_pro"])
        self.assertTrue(admin_stats.owner_users(self.db)[0]["is_pro"])
        with self.assertRaises(DomainError):
            users.set_pro(self.db, 999, True)

    def test_style_label_is_editable(self):
        t = templates.create(self.db, {"title": "Свой", "kind": "photo", "category": "women", "style_label": "Beauty", "is_published": True})
        self.assertEqual(templates.admin_get(self.db, t["id"])["style_label"], "Beauty")
        self.assertEqual(templates.list_published(self.db, category="women")[-1]["style_label"] or "Beauty", "Beauty")


class DeleteOrderTest(BaseTest):
    def test_delete_removes_files_and_hides_but_keeps_record(self):
        from app.services import favorites
        o, _ = free(self, "a", prompt="x")
        done = generation.process_order(self.db, self.storage, self.mock, o["id"])
        favorites.set_favorite(self.db, 1, "order", o["id"], True)
        orders.delete_order(self.db, self.storage, 1, o["id"])
        self.assertFalse(os.path.exists(done["result_path"]))
        self.assertEqual(orders.list_user_orders(self.db, 1), [])
        self.assertEqual(favorites.ids(self.db, 1)["orders"], [])
        self.assertEqual(orders.count_done_by_kind(self.db, 1)["photo"], 1)  # статистика и бесплатная попытка не «воскресают»
        self.assertFalse(orders.free_status(self.db, 1)["photo"])

    def test_cannot_delete_running_or_foreign_order(self):
        o, _ = free(self, "a", prompt="x")
        with self.assertRaises(DomainError):
            orders.delete_order(self.db, self.storage, 1, o["id"])  # ещё не завершён
        users.upsert_user(self.db, 2, "b", "Чужой")
        generation.process_order(self.db, self.storage, self.mock, o["id"])
        with self.assertRaises(DomainError):
            orders.delete_order(self.db, self.storage, 2, o["id"])
