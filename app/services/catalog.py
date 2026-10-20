"""Каталог платформы: эффекты, тренды, фотосессии, промпты, маркетинг, сцены аватаров — и общий поиск.

Всё хранится в таблице templates (поле section) и редактируется в админ-панели. Здесь только чтение для пользователя."""
from __future__ import annotations

import json

from .. import catalog_data as cd
from ..db import Database
from ..errors import DomainError
from .templates import media_kind

SECTION_LABELS = {
    "idea": "Идеи",
    "effect": "Эффекты", "trend": "Тренды", "photoshoot": "Фотосессии", "prompt": "Промпты", "marketing": "Маркетинг", "mtool": "Маркетинг",
    "avatar": "Аватары",
}


def _tag_map(section: str) -> dict[str, str]:
    tags = cd.SECTION_TAGS.get("marketing" if section == "mtool" else section, [])
    return dict(tags)


def _loads(raw, default):
    try:
        return json.loads(raw or "")
    except (ValueError, TypeError):
        return default


def public(t: dict, uses: int = 0) -> dict:
    labels = _tag_map(t["section"])
    out = {
        "id": t["id"], "title": t["title"], "description": t["description"] if t["section"] != "prompt" else "",
        "section": t["section"], "tag": t["tag"], "tag_label": labels.get(t["tag"], ""),
        "tool": t["tool"].split(":", 1)[0] if t["tool"] else "", "kind": t["kind"], "price_credits": t["price_credits"],
        "required": [{"code": c, "label": cd.MATERIALS.get(c, c)} for c in _loads(t["required"], []) if c != "avatar"],
        "needs_avatar": "avatar" in _loads(t["required"], []),
        "preview_url": t["preview_url"], "preview_kind": media_kind(t["preview_url"]) if t["preview_url"] else "image",
        "is_popular": bool(t["is_popular"]), "featured": bool(t["is_popular"]), "uses": uses, "slug": t["slug"],
    }
    if t["section"] == "prompt":
        out["prompt"] = t["prompt"]
        out["supported_models"] = _loads(t["supported_models"], [])
    return out


def _prices(db: Database, items: list[dict]) -> list[dict]:
    """Цена промпта — это цена самой доступной из поддерживаемых моделей (у самого промпта цены нет)."""
    if not any(i["section"] == "prompt" for i in items):
        return items
    with db.read() as c:
        price = {r["name"]: r["price_credits"] for r in c.execute("SELECT name, price_credits FROM ai_models WHERE is_active = 1 AND kind = 'photo'")}
    for i in items:
        if i["section"] == "prompt":
            known = [price[m] for m in i.get("supported_models", []) if m in price]
            i["price_credits"] = min(known) if known else 0
    return items


def _uses(db: Database) -> dict[int, int]:
    with db.read() as c:
        return {r[0]: r[1] for r in c.execute("SELECT template_id, COUNT(*) FROM orders WHERE status != 'failed' GROUP BY template_id")}


def list_items(db: Database, section: str, tag: str | None = None, q: str | None = None, popular: bool = False, limit: int | None = None,
               on_home: bool = False, on_ideas: bool = False) -> list[dict]:
    if section not in cd.SECTIONS:
        raise DomainError("Неизвестный раздел", code="not_found", status=404)
    sql, args = "SELECT * FROM templates WHERE is_published = 1 AND is_system = 0 AND section = ?", [section]
    if tag and tag not in ("all", "popular"):
        sql += " AND tag = ?"; args.append(tag)
    if popular or tag == "popular":
        sql += " AND is_popular = 1"
    if on_home:
        sql += " AND on_home = 1"
    if on_ideas:
        sql += " AND on_ideas = 1"
    sql += " ORDER BY is_popular DESC, sort_order, id"  # «Рекомендуем» — выше остальных
    with db.read() as conn:
        rows = [dict(r) for r in conn.execute(sql, args).fetchall()]
    if q:
        needle = q.strip().casefold()
        rows = [r for r in rows if needle in r["title"].casefold() or needle in r["description"].casefold() or (section == "prompt" and needle in r["prompt"].casefold())]
    if limit:
        rows = rows[:limit]
    uses = _uses(db)
    return _prices(db, [public(r, uses.get(r["id"], 0)) for r in rows])


def get_item(db: Database, item_id: int) -> dict:
    with db.read() as conn:
        row = conn.execute("SELECT * FROM templates WHERE id = ? AND is_published = 1 AND is_system = 0 AND section != 'legacy'", (item_id,)).fetchone()
    if row is None:
        raise DomainError("Не найдено или снято с публикации", code="not_found", status=404)
    return _prices(db, [public(dict(row), _uses(db).get(item_id, 0))])[0]


def get_by_slug(db: Database, slug: str) -> dict:
    with db.read() as conn:
        row = conn.execute("SELECT id FROM templates WHERE slug = ? AND is_published = 1", (slug,)).fetchone()
    if row is None:
        raise DomainError("Не найдено", code="not_found", status=404)
    return get_item(db, row["id"])


def meta(db: Database) -> dict:
    """Категории разделов с числом опубликованных карточек (пустые категории интерфейс может скрыть)."""
    with db.read() as conn:
        rows = conn.execute("SELECT section, tag, COUNT(*) AS n, SUM(is_popular) AS pop FROM templates "
                            "WHERE is_published = 1 AND is_system = 0 AND section != 'legacy' GROUP BY section, tag").fetchall()
        mrows = conn.execute("SELECT kind, tags FROM ai_models WHERE is_active = 1").fetchall()
    counts: dict[str, dict[str, int]] = {}
    popular: dict[str, int] = {}
    for r in rows:
        counts.setdefault(r["section"], {})[r["tag"]] = r["n"]
        popular[r["section"]] = popular.get(r["section"], 0) + (r["pop"] or 0)
    sections = {}
    for sec, tags in cd.SECTION_TAGS.items():
        c = counts.get(sec, {}) | ({k: counts.get("mtool", {}).get(k, 0) + counts.get(sec, {}).get(k, 0) for k in counts.get("mtool", {})} if sec == "marketing" else {})
        sections[sec] = {"tags": [{"id": k, "label": v, "count": c.get(k, 0)} for k, v in tags],
                         "total": sum(c.values()), "popular": popular.get(sec, 0)}
    mcount: dict[str, dict[str, int]] = {}
    for r in mrows:
        for t in _loads(r["tags"], []):
            mcount.setdefault(r["kind"], {})[t] = mcount.get(r["kind"], {}).get(t, 0) + 1
    models = {kind: {"tags": [{"id": k, "label": v, "count": mcount.get(kind, {}).get(k, 0)} for k, v in tags]} for kind, tags in cd.MODEL_TAGS.items()}
    return {"sections": sections, "models": models, "materials": cd.MATERIALS,
            "audio": {"voices": [{"id": k, "label": v} for k, v in cd.VOICES], "emotions": [{"id": k, "label": v} for k, v in cd.EMOTIONS],
                      "tones": [{"id": k, "label": v} for k, v in cd.TONES]},
            "quick_actions": [{"title": t, "text": d, "action": a} for t, d, a in cd.QUICK_ACTIONS]}


def search(db: Database, user_id: int, q: str, per_group: int = 6) -> list[dict]:
    """Глобальный поиск (Ctrl/Cmd+K): модели, промпты, эффекты, тренды, фотосессии, маркетинг и собственная история."""
    needle = (q or "").strip().casefold()
    if len(needle) < 2:
        return []
    groups: list[dict] = []
    with db.read() as conn:
        models = [dict(r) for r in conn.execute("SELECT id, name, kind, description FROM ai_models WHERE is_active = 1 ORDER BY sort_order, id")]
        items = [dict(r) for r in conn.execute("SELECT * FROM templates WHERE is_published = 1 AND is_system = 0 AND section != 'legacy' ORDER BY sort_order, id")]
        hist = [dict(r) for r in conn.execute(
            "SELECT o.id, o.kind, o.prompt, o.status, t.title FROM orders o JOIN templates t ON t.id = o.template_id "
            "WHERE o.user_id = ? AND o.is_hidden = 0 ORDER BY o.id DESC LIMIT 300", (user_id,))]
    hit = [m for m in models if needle in m["name"].casefold() or needle in m["description"].casefold()][:per_group]
    if hit:
        groups.append({"type": "model", "label": "Модели", "items": [{"id": m["id"], "title": m["name"], "subtitle": {"photo": "Изображения", "video": "Видео", "audio": "Аудио"}[m["kind"]], "kind": m["kind"]} for m in hit]})
    for sec, label in (("prompt", "Промпты"), ("effect", "Эффекты"), ("trend", "Тренды"), ("photoshoot", "Фотосессии"), ("marketing", "Маркетинг")):
        pool = [t for t in items if t["section"] == sec or (sec == "marketing" and t["section"] == "mtool")]
        found = [t for t in pool if needle in t["title"].casefold() or needle in t["description"].casefold() or (sec == "prompt" and needle in t["prompt"].casefold())][:per_group]
        if found:
            groups.append({"type": sec, "label": label, "items": [{"id": t["id"], "title": t["title"], "subtitle": t["tag"] and _tag_map(t["section"]).get(t["tag"], "").capitalize(), "slug": t["slug"]} for t in found]})
    mine = [h for h in hist if needle in (h["prompt"] or "").casefold() or needle in h["title"].casefold()][:per_group]
    if mine:
        groups.append({"type": "history", "label": "История", "items": [{"id": h["id"], "title": (h["prompt"] or h["title"])[:80], "subtitle": h["title"], "kind": h["kind"]} for h in mine]})
    return groups
