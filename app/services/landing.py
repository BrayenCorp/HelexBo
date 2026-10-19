"""Данные главной страницы-лендинга. Ничего не выдумывается: если в базе нет моделей, примеров или пакетов,
соответствующий блок приходит пустым и интерфейс его не показывает."""
from __future__ import annotations

from ..config import Settings
from ..db import Database
from . import categories, content, methods, models, payments, showcase, templates


def build(db: Database, settings: Settings, bot_present: bool) -> dict:
    blocks = content.get_all(db)
    cats = categories.list_public(db)
    ai_models = models.public_list(db)
    with db.read() as c:
        uses = {r[0]: r[1] for r in c.execute("SELECT template_id, COUNT(*) FROM orders GROUP BY template_id")}
        sys_price = {r["kind"]: r["price_credits"] for r in c.execute("SELECT kind, price_credits FROM templates WHERE is_system = 1 AND is_published = 1")}
        cat_of = {r["id"]: r["category"] for r in c.execute("SELECT id, category FROM templates")}
    trends = []
    for t in templates.list_flagged(db, "is_trend", 12):
        trends.append({"id": t["id"], "title": t["title"], "description": t["description"], "preview_url": t["preview_url"], "kind": t["kind"],
                       "uses": uses.get(t["id"], 0)})
    works = [{"id": f"s{w['id']}", "title": w["title"], "media_url": w["media_url"], "kind": "video" if w["media_kind"] == "video" else "photo",
              "template_id": w["template_id"], "prompt": w["prompt"], "category": cat_of.get(w["template_id"])} for w in showcase.list_public(db)]
    if not works:  # без своих примеров показываем только реальные превью опубликованных стилей
        works = [{"id": f"t{t['id']}", "title": t["title"], "media_url": t["preview_url"], "kind": t["kind"], "template_id": t["id"], "prompt": "",
                  "category": t["category"]} for t in templates.list_published(db, limit=60) if t["preview_url"]][:24]
    price_from: dict = {}
    for kind in ("photo", "video"):
        prices = [m["price_credits"] for m in ai_models if m["kind"] == kind] or ([sys_price[kind]] if kind in sys_price else [])
        if prices:
            price_from[kind] = min(prices)
    chooser = []
    first = lambda kind: next((m for m in ai_models if m["kind"] == kind), None)
    if first("photo"):
        chooser.append({"title": "Хочу реалистичную фотографию", "action": {"type": "model", "model_id": first("photo")["id"], "kind": "photo"}})
    if any(t["style_label"] == "Fashion" for t in templates.list_published(db, category="women")):
        chooser.append({"title": "Хочу fashion", "action": {"type": "category", "id": "women"}})
    if first("video"):
        chooser.append({"title": "Хочу видео", "action": {"type": "model", "model_id": first("video")["id"], "kind": "video"}})
    chooser.append({"title": "Хочу изменить фото", "action": {"type": "generate", "kind": "photo"}})
    return {
        "content": blocks, "categories": cats, "models": ai_models, "trends": trends, "works": works, "chooser": chooser,
        "work_categories": [{"id": c["id"], "title": c["title"]} for c in cats if any(w["category"] == c["id"] for w in works)],
        "price_from": price_from, "packages": payments.list_packages(db), "methods": methods.for_users(db, settings, bot_present),
        "faq": content.faq_public(db),
        "banner": {"banner_image_url": __import__("app.services.site_settings", fromlist=["x"]).get_all(db).get("banner_image_url", "")},
    }
