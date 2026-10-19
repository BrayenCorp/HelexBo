"""Функции экранов Luma: избранное, стили, примеры, пакеты, поиск, приватность."""
import os

from app.errors import DomainError
from app.services import credits, favorites, generation, orders, payments, templates
from tests.helpers import BaseTest


class FavoritesTest(BaseTest):
    def test_template_favorite_toggle(self):
        tid = self.tpl()
        self.assertEqual(favorites.set_favorite(self.db, 1, "template", tid, True)["templates"], [tid])
        favorites.set_favorite(self.db, 1, "template", tid, True)  # повтор не создаёт дубль
        self.assertEqual(favorites.ids(self.db, 1)["templates"], [tid])
        self.assertEqual(favorites.list_all(self.db, 1)["templates"][0]["id"], tid)
        self.assertEqual(favorites.set_favorite(self.db, 1, "template", tid, False)["templates"], [])

    def test_unpublished_template_cannot_be_favorited(self):
        tid = self.tpl()
        templates.update(self.db, tid, {"is_published": False})
        with self.assertRaises(DomainError):
            favorites.set_favorite(self.db, 1, "template", tid, True)

    def test_only_own_done_result_can_be_favorited(self):
        o, _ = self.submit("a")
        with self.assertRaises(DomainError):  # ещё не готов
            favorites.set_favorite(self.db, 1, "order", o["id"], True)
        generation.process_order(self.db, self.storage, self.mock, o["id"])
        favorites.set_favorite(self.db, 1, "order", o["id"], True)
        from app.services import users
        users.upsert_user(self.db, 2, "x", "Чужой")
        with self.assertRaises(DomainError):  # чужой результат
            favorites.set_favorite(self.db, 2, "order", o["id"], True)
        self.assertEqual(len(favorites.list_all(self.db, 1)["results"]), 1)

    def test_deleting_template_clears_favorites(self):
        t = templates.create(self.db, {"title": "Временный", "kind": "photo", "is_published": True})
        favorites.set_favorite(self.db, 1, "template", t["id"], True)
        templates.delete(self.db, t["id"])
        self.assertEqual(favorites.ids(self.db, 1)["templates"], [])


class StylesAndExamplesTest(BaseTest):
    def test_default_style_used_and_unknown_rejected(self):
        tid = self.tpl()
        o, _ = self.submit("a", template_id=tid)
        self.assertEqual(o["style"], "classic")
        self.add_balance(1, 20)
        o2, _ = orders.submit_generation(self.db, self.storage, user_id=1, template_id=tid, request_id="b",
                                         image_bytes=__import__("tests.helpers", fromlist=["x"]).make_photo(), source="app", style="soft")
        self.assertEqual(o2["style"], "soft")
        with self.assertRaises(DomainError):
            orders.submit_generation(self.db, self.storage, user_id=1, template_id=tid, request_id="c",
                                     image_bytes=__import__("tests.helpers", fromlist=["x"]).make_photo(), source="app", style="nope")
        self.assertEqual(credits.get_balance(self.db, 1), 20 - o2["price_credits"])

    def test_style_prompt_is_appended(self):
        tid = self.tpl()
        captured = {}

        class Spy:
            def get(self_inner, kind, model):
                class P:
                    def generate(_, req):
                        captured["prompt"] = req.prompt
                        return self.mock.get(kind, model).generate(req)
                return P()

        self.add_balance(1, 20)
        self.submit("free")
        from tests.helpers import make_photo
        o, _ = orders.submit_generation(self.db, self.storage, user_id=1, template_id=tid, request_id="x",
                                        image_bytes=make_photo(), source="app", style="cinema")
        generation.process_order(self.db, self.storage, Spy(), o["id"])
        self.assertIn("cinematic lighting", captured["prompt"])

    def test_styles_editable_and_validated(self):
        t = templates.create(self.db, {"title": "Свой", "kind": "photo", "is_published": True,
                                       "styles": [{"title": "Тёплый", "prompt": "warm"}, {"title": "Холодный"}]})
        full = templates.admin_get(self.db, t["id"])
        self.assertEqual([s["title"] for s in full["styles"]], ["Тёплый", "Холодный"])
        self.assertEqual(len({s["id"] for s in full["styles"]}), 2)
        with self.assertRaises(DomainError):
            templates.update(self.db, t["id"], {"styles": [{"title": ""}]})
        with self.assertRaises(DomainError):
            templates.update(self.db, t["id"], {"styles": [{"title": str(i)} for i in range(20)]})
        self.assertEqual(templates.get_published(self.db, t["id"])["styles"][0]["title"], "Тёплый")

    def test_examples_saved_replaced_and_validated(self):
        t = templates.create(self.db, {"title": "С примерами", "kind": "photo", "is_published": True,
                                       "examples": ["/media/a.jpg", "/media/b.mp4"]})
        ex = templates.get_published(self.db, t["id"])["examples"]
        self.assertEqual([e["kind"] for e in ex], ["image", "video"])
        templates.update(self.db, t["id"], {"examples": ["/media/c.jpg"]})
        self.assertEqual(len(templates.get_published(self.db, t["id"])["examples"]), 1)
        with self.assertRaises(DomainError):
            templates.update(self.db, t["id"], {"examples": ["http://insecure/x.jpg"]})
        templates.delete(self.db, t["id"])  # примеры удаляются вместе с шаблоном


class CatalogSearchTest(BaseTest):
    def test_search_is_case_insensitive_for_cyrillic(self):
        found = templates.list_published(self.db, q="ПРИНЦ")
        self.assertTrue(any("принц" in t["title"].lower() for t in found))
        self.assertEqual(templates.list_published(self.db, q="такого-нет-нигде"), [])

    def test_collections(self):
        self.assertTrue(all(t["is_popular"] for t in templates.list_published(self.db, collection="popular")))
        self.assertTrue(all(t["is_trend"] for t in templates.list_published(self.db, collection="trend")))
        self.assertLessEqual(len(templates.list_published(self.db, collection="new")), 24)


class PackagesAdminTest(BaseTest):
    def test_package_crud_and_badge(self):
        p = payments.create_package(self.db, {"title": "Мини", "credits": 5, "price_stars": 25, "badge": "Выгодно"})
        self.assertIn("Выгодно", [x["badge"] for x in payments.list_packages(self.db)])
        payments.update_package(self.db, p["id"], {"is_active": False})
        self.assertNotIn(p["id"], [x["id"] for x in payments.list_packages(self.db)])
        with self.assertRaises(DomainError):
            payments.create_package(self.db, {"title": "X", "credits": 0, "price_stars": 1})
        self.assertTrue(payments.delete_package(self.db, p["id"])["deleted"])

    def test_package_with_sales_is_hidden_not_deleted(self):
        pay = payments.create_payment(self.db, 1, "p10", "test")
        payments.confirm_payment(self.db, pay["payload"], provider="test")
        res = payments.delete_package(self.db, "p10")
        self.assertEqual((res["deleted"], res["hidden"]), (False, True))
        self.assertEqual(len(payments.list_user_payments(self.db, 1)), 1)  # история цела

    def test_default_badges_seeded(self):
        badges = {p["id"]: p["badge"] for p in payments.list_packages(self.db)}
        self.assertEqual(badges["p30"], "Популярный")
        self.assertEqual(badges["p100"], "Лучший выбор")


class PrivacyTest(BaseTest):
    def test_source_photo_deleted_after_processing(self):
        o, _ = self.submit("a")
        path = o["input_path"]
        self.assertTrue(os.path.exists(path))
        done = generation.process_order(self.db, self.storage, self.mock, o["id"])
        self.assertFalse(os.path.exists(path))
        self.assertIsNone(done["input_path"])

    def test_source_photo_deleted_also_on_failure(self):
        o, _ = self.submit("a")
        path = o["input_path"]
        generation.process_order(self.db, self.storage, self.live, o["id"])
        self.assertFalse(os.path.exists(path))

    def test_delete_my_media_removes_files_but_keeps_balance_and_history(self):
        o, _ = self.submit("a")
        done = generation.process_order(self.db, self.storage, self.mock, o["id"])
        favorites.set_favorite(self.db, 1, "order", o["id"], True)
        self.add_balance(1, 5)
        n = orders.delete_user_media(self.db, self.storage, 1)
        self.assertEqual(n, 1)
        self.assertFalse(os.path.exists(done["result_path"]))
        self.assertEqual(credits.get_balance(self.db, 1), 5)
        self.assertEqual(len(orders.list_user_orders(self.db, 1)), 1)
        self.assertFalse(orders.public_order(orders.get_user_order(self.db, 1, o["id"]))["has_result"])
        self.assertEqual(favorites.ids(self.db, 1)["orders"], [])
        self.assertFalse(orders.free_status(self.db, 1)["photo"])  # бесплатная попытка уже была использована
