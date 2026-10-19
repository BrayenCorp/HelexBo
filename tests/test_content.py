"""Контент R STUDIO: категории, шаблоны, витрина, баннер, загрузка медиа, миграция старой базы."""
import io

from PIL import Image

from app.db import SCHEMA, Database, init_db
from app.errors import DomainError, InvalidImage
from app.seed import CATEGORIES_V4
from app.services import categories, media, orders, showcase, site_settings, templates, users
from tests.helpers import BaseTest, make_photo


class SeedTest(BaseTest):
    def test_six_categories_of_nolla_and_all_have_templates(self):
        cats = categories.list_public(self.db)
        self.assertEqual([c["title"] for c in cats], [t for _, t, _, _ in CATEGORIES_V4])
        self.assertEqual([c["title"] for c in cats], ["Тренды", "Мужские", "Женские", "Детские", "Семейные", "Видео"])
        for c in cats:
            self.assertGreater(c["count"], 0, c["title"])
            self.assertTrue(c["description"], c["title"])

    def test_old_categories_hidden_not_deleted_and_templates_moved(self):
        hidden = {c["id"] for c in categories.admin_list(self.db) if not c["is_published"]}
        self.assertTrue({"fashion", "wedding", "love-story", "seasonal"} <= hidden)
        with self.db.read() as conn:
            row = conn.execute("SELECT category, style_label FROM templates WHERE slug = 'fashion-editorial'").fetchone()
        self.assertEqual((row["category"], row["style_label"]), ("women", "Editorial"))

    def test_women_and_men_have_the_eight_styles(self):
        want = {"Portrait", "Fashion", "Lifestyle", "Studio", "Cinematic", "Street", "Beauty", "Editorial"}
        for cat in ("women", "men"):
            labels = {t["style_label"] for t in templates.list_published(self.db, category=cat)}
            self.assertTrue(want <= labels, (cat, want - labels))

    def test_home_collections_exist(self):
        self.assertTrue(templates.list_flagged(self.db, "is_popular"))
        self.assertTrue(templates.list_flagged(self.db, "is_trend"))
        self.assertIn("banner_title", site_settings.get_all(self.db))

    def test_seed_runs_once_deleted_templates_stay_deleted(self):
        t = templates.list_published(self.db)[0]
        templates.delete(self.db, t["id"])
        init_db(self.db)  # «перезапуск»
        self.assertNotIn(t["id"], [x["id"] for x in templates.list_published(self.db)])

    def test_legacy_database_is_migrated_without_losing_data(self):
        import tempfile, os
        with tempfile.TemporaryDirectory() as d:
            db = Database(os.path.join(d, "old.db"))
            with db.read() as conn:
                conn.executescript(SCHEMA)
                for table, col in (("templates", "is_trend"), ("templates", "styles"), ("orders", "style"),
                                   ("categories", "description"), ("packages", "badge")):
                    if table == "categories":
                        continue  # ниже пересоздаётся целиком
                    conn.execute(f"ALTER TABLE {table} DROP COLUMN {col}")
                for t in ("categories", "showcase", "settings", "favorites", "template_examples"):
                    conn.execute(f"DROP TABLE {t}")
                conn.execute("INSERT INTO users (tg_id, first_name, balance, created_at) VALUES (5, 'Старый', 7, 'x')")
                for slug, cat, kind in (("cartoon-hero", "cartoon", "photo"), ("legacy-custom", "fairy", "photo"), ("video-alive", "trends", "video")):
                    conn.execute(
                        "INSERT INTO templates (slug, title, category, kind, is_published, created_at, updated_at) "
                        "VALUES (?, ?, ?, ?, 1, 'x', 'x')", (slug, slug, cat, kind))
            init_db(db)
            with db.read() as conn:
                cat = {r["slug"]: r["category"] for r in conn.execute("SELECT slug, category FROM templates")}
                bal = conn.execute("SELECT balance FROM users WHERE tg_id = 5").fetchone()["balance"]
            self.assertEqual(cat["cartoon-hero"], "kids")
            self.assertEqual(cat["legacy-custom"], "kids")  # собственный шаблон не потерян
            self.assertEqual(cat["video-alive"], "ai-video")
            self.assertIn("kid-prince", cat)  # шаблоны из макета Luma добавлены
            self.assertIn("fashion-editorial", cat)  # новые шаблоны добавлены
            self.assertEqual(bal, 7)
            self.assertEqual(len(categories.list_public(db)), 6)
            self.assertIn("__free_photo", cat)  # системные шаблоны свободной генерации созданы


class AdminContentTest(BaseTest):
    def test_category_crud_and_delete_guard(self):
        c = categories.create(self.db, {"title": "Новая", "cover_url": "/media/x.jpg"})
        categories.update(self.db, c["id"], {"title": "Новая 2", "is_published": False})
        self.assertNotIn(c["id"], [x["id"] for x in categories.list_public(self.db)])
        with self.assertRaises(DomainError):
            categories.delete(self.db, "women")  # в ней есть шаблоны
        categories.delete(self.db, c["id"])
        with self.assertRaises(DomainError):
            categories.create(self.db, {"title": " "})

    def test_template_category_must_exist(self):
        with self.assertRaises(DomainError):
            templates.create(self.db, {"title": "X", "kind": "photo", "category": "nope"})
        t = templates.create(self.db, {"title": "X", "kind": "photo", "category": "men", "is_trend": True})
        self.assertEqual(t["category"], "men")
        self.assertEqual(t["is_trend"], 1)
        with self.assertRaises(DomainError):
            templates.update(self.db, t["id"], {"category": "nope"})

    def test_delete_template_without_orders_removes_it(self):
        t = templates.create(self.db, {"title": "Временный", "kind": "photo"})
        self.assertEqual(templates.delete(self.db, t["id"]), {"deleted": True, "hidden": False, "orders": 0})
        self.assertNotIn(t["id"], [x["id"] for x in templates.admin_list(self.db)])

    def test_delete_template_with_orders_only_hides_it(self):
        tid = self.tpl()
        self.submit("a", template_id=tid)
        res = templates.delete(self.db, tid)
        self.assertEqual((res["deleted"], res["hidden"]), (False, True))
        self.assertNotIn(tid, [x["id"] for x in templates.list_published(self.db)])
        self.assertEqual(len(orders.list_user_orders(self.db, 1)), 1)  # история цела

    def test_showcase_crud_validation_and_template_link(self):
        with self.assertRaises(DomainError):
            showcase.create(self.db, {"media_url": "http://insecure/x.jpg"})
        with self.assertRaises(DomainError):
            showcase.create(self.db, {"media_url": "/media/a.jpg", "template_id": 99999})
        tid = self.tpl()
        item = showcase.create(self.db, {"media_url": "/media/a.mp4", "title": "Пример", "template_id": tid})
        pub = showcase.list_public(self.db)
        self.assertEqual((pub[0]["media_kind"], pub[0]["template_id"]), ("video", tid))
        templates.update(self.db, tid, {"is_published": False})  # скрытый шаблон — не показываем ссылку на него
        self.assertEqual(showcase.list_public(self.db), [])
        showcase.update(self.db, item["id"], {"template_id": None})
        self.assertEqual(len(showcase.list_public(self.db)), 1)
        showcase.delete(self.db, item["id"])
        self.assertEqual(showcase.admin_list(self.db), [])

    def test_banner_settings_update_and_limits(self):
        out = site_settings.update(self.db, {"banner_title": "Привет", "evil_key": "x", "banner_text": "я" * 999})
        self.assertEqual(out["banner_title"], "Привет")
        self.assertEqual(len(out["banner_text"]), 300)
        self.assertNotIn("evil_key", out)


class MediaTest(BaseTest):
    LIM = dict(max_image=5_000_000, max_video=1_000_000)

    def test_image_saved_as_clean_jpeg(self):
        buf = io.BytesIO()
        Image.new("RGBA", (300, 200), (10, 20, 30, 128)).save(buf, "PNG")
        res = media.save_media(self.storage, buf.getvalue(), **self.LIM)
        self.assertEqual(res["kind"], "image")
        self.assertTrue(res["url"].startswith("/media/") and res["url"].endswith(".jpg"))
        self.assertTrue((self.storage.media / res["url"].split("/")[-1]).exists())

    def test_video_accepted_by_signature_and_size_limit(self):
        mp4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 100
        self.assertEqual(media.save_media(self.storage, mp4, **self.LIM)["kind"], "video")
        webm = b"\x1a\x45\xdf\xa3" + b"\x00" * 100
        self.assertTrue(media.save_media(self.storage, webm, **self.LIM)["url"].endswith(".webm"))
        with self.assertRaises(InvalidImage):
            media.save_media(self.storage, mp4 + b"\x00" * 2_000_000, **self.LIM)

    def test_garbage_and_html_rejected(self):
        for bad in (b"", b"<html><script>alert(1)</script></html>", b"MZ\x90\x00 exe"):
            with self.assertRaises(InvalidImage):
                media.save_media(self.storage, bad, **self.LIM)
