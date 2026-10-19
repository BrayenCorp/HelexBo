import os

from app.errors import DomainError, InvalidImage, TemplateNotFound
from app.services import admin_stats, generation, orders, templates
from tests.helpers import BaseTest, make_photo


class OrdersTest(BaseTest):
    def test_lifecycle_mock_photo_and_video(self):
        for kind in ("photo", "video"):
            o, created = self.submit(f"r-{kind}", kind=kind)
            self.assertTrue(created)
            self.assertEqual(o["status"], "created")
            done = generation.process_order(self.db, self.storage, self.mock, o["id"])
            self.assertEqual(done["status"], "done")
            self.assertEqual(done["is_stub"], 1)  # тестовый режим помечается явно
            self.assertTrue(os.path.exists(done["result_path"]))
            self.assertEqual(done["result_mime"], "image/jpeg" if kind == "photo" else "image/gif")

    def test_processing_same_order_twice_is_safe(self):
        o, _ = self.submit("a")
        first = generation.process_order(self.db, self.storage, self.mock, o["id"])
        second = generation.process_order(self.db, self.storage, self.mock, o["id"])
        self.assertEqual(first["result_path"], second["result_path"])

    def test_unconfigured_provider_fails_and_refunds(self):
        self.submit("free")
        self.add_balance(1, 10)
        o, _ = self.submit("paid", template_id=self.tpl(price=3))
        res = generation.process_order(self.db, self.storage, self.live, o["id"])
        self.assertEqual(res["status"], "failed")
        self.assertIn("ключ", res["error"])  # нет API-ключа → честная ошибка, а не «демо»
        from app.services import credits
        self.assertEqual(credits.get_balance(self.db, 1), 10)
        self.assertTrue(self.balance_matches_ledger())
        self.assertEqual(len(admin_stats.dev_errors(self.db)), 1)

    def test_provider_exception_refunds(self):
        class Boom:
            def get(self, kind, model):
                raise RuntimeError("API упал")

        self.submit("free")
        self.add_balance(1, 10)
        o, _ = self.submit("paid", template_id=self.tpl(price=3))
        res = generation.process_order(self.db, self.storage, Boom(), o["id"])
        self.assertEqual(res["status"], "failed")
        from app.services import credits
        self.assertEqual(credits.get_balance(self.db, 1), 10)

    def test_unfinished_orders_recovered_on_startup(self):
        self.submit("free")
        self.add_balance(1, 10)
        o, _ = self.submit("paid", template_id=self.tpl(price=3))
        orders.claim_for_processing(self.db, o["id"])  # «процесс упал» посреди генерации
        self.assertEqual(orders.fail_unfinished_orders(self.db, "restart"), 2)
        from app.services import credits
        self.assertEqual(credits.get_balance(self.db, 1), 10)
        self.assertEqual(orders.fail_unfinished_orders(self.db, "restart"), 0)

    def test_late_result_after_timeout_does_not_resurrect_order(self):
        o, _ = self.submit("a")
        orders.claim_for_processing(self.db, o["id"])
        orders.fail_order(self.db, o["id"], "timeout")
        ok = orders.complete_order(self.db, o["id"], result_path="x", mime="image/jpeg", provider="p", cost_usd=0, is_stub=False)
        self.assertFalse(ok)
        self.assertEqual(orders.get_order(self.db, o["id"])["status"], "failed")

    def test_unpublished_or_missing_template_rejected(self):
        tid = self.tpl()
        templates.update(self.db, tid, {"is_published": False})
        with self.assertRaises(TemplateNotFound):
            self.submit("a", template_id=tid)
        with self.assertRaises(TemplateNotFound):
            self.submit("b", template_id=99999)

    def test_bad_images_rejected(self):
        for bad in (b"not an image", make_photo((10, 10))):
            with self.assertRaises(InvalidImage):
                orders.submit_generation(self.db, self.storage, user_id=1, template_id=self.tpl(),
                                         request_id="x", image_bytes=bad, source="bot")
        with self.assertRaises(InvalidImage):
            orders.submit_generation(self.db, self.storage, user_id=1, template_id=self.tpl(),
                                     request_id="y", image_bytes=make_photo(), source="bot", max_bytes=10)

    def test_failed_submit_leaves_no_files(self):
        before = len(os.listdir(self.storage.uploads))
        with self.assertRaises(TemplateNotFound):
            self.submit("a", template_id=99999)
        self.assertEqual(len(os.listdir(self.storage.uploads)), before)

    def test_template_admin_validation(self):
        with self.assertRaises(DomainError):
            templates.create(self.db, {"title": "", "kind": "photo"})
        with self.assertRaises(DomainError):
            templates.update(self.db, self.tpl(), {"price_credits": -1})
        t = templates.create(self.db, {"title": "Новый", "kind": "video", "price_credits": 7, "is_published": True})
        self.assertEqual(t["model"], "video-default")
        self.assertIn(t["id"], [x["id"] for x in templates.list_published(self.db, kind="video")])

    def test_public_template_hides_prompt_and_model(self):
        pub = templates.list_published(self.db)[0]
        self.assertNotIn("prompt", pub)
        self.assertNotIn("model", pub)
