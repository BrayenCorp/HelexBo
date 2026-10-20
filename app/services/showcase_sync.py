"""Перенос витрины из кода (app/showcase.py) в базу.

Запускается при старте сервера. Карточка узнаётся по slug: новая — добавится, изменённая — обновится,
удалённая из файла — скроется (история заказов по ней сохраняется).
Руками в базе витрину править не нужно: файл — источник правды.
"""
from __future__ import annotations

import json
import logging

from ..db import Database, now
from ..showcase import SHOWCASE

log = logging.getLogger(__name__)

KINDS = {"photo", "video", "audio"}
DEFAULT_MODEL = {"photo": "image-default", "video": "video-default", "audio": "audio-default"}
FIELDS = ("title", "description", "category", "kind", "prompt", "model", "price", "image", "needs", "featured", "on_home", "hidden")


def _model_for(conn, card: dict) -> str:
    """Модель можно указать названием («Nano Banana 2») или служебным ключом."""
    raw = (card.get("model") or "").strip()
    if not raw or raw in ("image-default", "video-default", "audio-default", "seedance-2.5"):
        return raw or DEFAULT_MODEL[card["kind"]]
    row = conn.execute("SELECT provider_key FROM ai_models WHERE name = ? AND is_active = 1", (raw,)).fetchone()
    return row["provider_key"] if row else DEFAULT_MODEL[card["kind"]]


def _price_for(conn, card: dict) -> int:
    price = int(card.get("price") or 0)
    if price > 0:
        return price
    raw = (card.get("model") or "").strip()
    row = conn.execute("SELECT price_credits FROM ai_models WHERE name = ? AND is_active = 1", (raw,)).fetchone() if raw else None
    if row:
        return row["price_credits"]
    row = conn.execute("SELECT price_credits FROM ai_models WHERE kind = ? AND is_active = 1 ORDER BY sort_order LIMIT 1", (card["kind"],)).fetchone()
    return row["price_credits"] if row else 10


def _check(card: dict) -> None:
    for field in ("slug", "title", "description", "category", "kind"):
        if not str(card.get(field) or "").strip():
            raise ValueError(f"В карточке витрины не заполнено поле «{field}»: {card.get('slug') or card}")
    if card["kind"] not in KINDS:
        raise ValueError(f"У карточки {card['slug']} тип должен быть photo, video или audio")


def sync(db: Database) -> dict:
    """Возвращает, сколько карточек добавлено, обновлено и скрыто."""
    added = updated = hidden = 0
    ts = now()
    with db.tx() as conn:
        seen = []
        for i, card in enumerate(SHOWCASE):
            _check(card)
            slug, seen_slug = card["slug"], card["slug"]
            seen.append(seen_slug)
            data = {
                "title": card["title"][:120],
                "description": card["description"],
                "tag": card["category"],
                "kind": card["kind"],
                "prompt": card.get("prompt") or "",
                "model": _model_for(conn, card),
                "price_credits": _price_for(conn, card),
                "preview_url": card.get("image") or "",
                "required": json.dumps(list(card.get("needs") or []), ensure_ascii=False),
                "is_popular": 1 if card.get("featured") else 0,
                "on_home": 0 if card.get("on_home") is False else 1,
                "on_ideas": 1,
                "is_published": 0 if card.get("hidden") else 1,
                "sort_order": (i + 1) * 10,
                "section": "idea",
                "category": "trends",
                "emoji": "✦",
                "updated_at": ts,
            }
            row = conn.execute("SELECT id FROM templates WHERE slug = ?", (slug,)).fetchone()
            if row:
                conn.execute(f"UPDATE templates SET {', '.join(f'{k} = ?' for k in data)} WHERE id = ?", [*data.values(), row["id"]])
                updated += 1
            else:
                cols = ["slug", "created_at", *data.keys()]
                conn.execute(f"INSERT INTO templates ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})", [slug, ts, *data.values()])
                added += 1
        if seen:
            marks = ", ".join("?" * len(seen))
            cur = conn.execute(f"UPDATE templates SET is_published = 0, updated_at = ? WHERE section = 'idea' AND is_published = 1 "
                               f"AND slug NOT IN ({marks})", [ts, *seen])
            hidden = cur.rowcount or 0
    if added or updated or hidden:
        log.info("Витрина из app/showcase.py: добавлено %s, обновлено %s, скрыто %s", added, updated, hidden)
    return {"added": added, "updated": updated, "hidden": hidden}
