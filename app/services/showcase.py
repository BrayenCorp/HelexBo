"""Витрина: фото и видео примеров работ студии, которые владелец загружает сам."""
from __future__ import annotations

from ..db import Database, now
from ..errors import DomainError


def media_kind(url: str) -> str:
    return "video" if url.lower().split("?")[0].endswith((".mp4", ".webm", ".mov")) else "image"


def _public(r: dict) -> dict:
    return {"id": r["id"], "title": r["title"], "media_url": r["media_url"],
            "media_kind": media_kind(r["media_url"]), "template_id": r["template_id"],
            "prompt": r.get("prompt", "")}


def list_public(db: Database, limit: int = 30) -> list[dict]:
    with db.read() as conn:
        rows = conn.execute(
            "SELECT s.* FROM showcase s LEFT JOIN templates t ON t.id = s.template_id "
            "WHERE s.is_published = 1 AND (s.template_id IS NULL OR t.is_published = 1) "
            "ORDER BY s.sort_order, s.id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [_public(dict(r)) for r in rows]


def admin_list(db: Database) -> list[dict]:
    with db.read() as conn:
        rows = conn.execute("SELECT * FROM showcase ORDER BY sort_order, id DESC").fetchall()
    return [{**dict(r), "media_kind": media_kind(r["media_url"])} for r in rows]


def _clean(conn, fields: dict, partial: bool) -> dict:
    out: dict = {}
    if "media_url" in fields:
        url = str(fields["media_url"]).strip()
        if not (url.startswith("/media/") or url.startswith("https://")):
            raise DomainError("Загрузите файл или укажите https-ссылку на фото/видео")
        out["media_url"] = url
    elif not partial:
        raise DomainError("Не загружено фото или видео")
    if "title" in fields:
        out["title"] = str(fields["title"]).strip()[:120]
    if "prompt" in fields:
        out["prompt"] = str(fields["prompt"]).strip()[:500]
    if "sort_order" in fields:
        try:
            out["sort_order"] = int(fields["sort_order"])
        except (TypeError, ValueError):
            raise DomainError("Порядок должен быть числом")
    if "is_published" in fields:
        out["is_published"] = 1 if fields["is_published"] in (True, 1, "1", "true", "True") else 0
    if "template_id" in fields:
        tid = fields["template_id"]
        if tid in (None, "", 0, "0"):
            out["template_id"] = None
        else:
            if conn.execute("SELECT 1 FROM templates WHERE id = ?", (int(tid),)).fetchone() is None:
                raise DomainError("Шаблон для ссылки не найден")
            out["template_id"] = int(tid)
    return out


def create(db: Database, fields: dict) -> dict:
    with db.tx() as conn:
        data = _clean(conn, fields, partial=False)
        cols = ["created_at", *data.keys()]
        cur = conn.execute(f"INSERT INTO showcase ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                           [now(), *data.values()])
        return dict(conn.execute("SELECT * FROM showcase WHERE id = ?", (cur.lastrowid,)).fetchone())


def update(db: Database, item_id: int, fields: dict) -> dict:
    with db.tx() as conn:
        if conn.execute("SELECT 1 FROM showcase WHERE id = ?", (item_id,)).fetchone() is None:
            raise DomainError("Элемент витрины не найден", code="not_found", status=404)
        data = _clean(conn, fields, partial=True)
        if data:
            conn.execute(f"UPDATE showcase SET {', '.join(f'{k} = ?' for k in data)} WHERE id = ?", [*data.values(), item_id])
        return dict(conn.execute("SELECT * FROM showcase WHERE id = ?", (item_id,)).fetchone())


def delete(db: Database, item_id: int) -> None:
    with db.tx() as conn:
        conn.execute("DELETE FROM showcase WHERE id = ?", (item_id,))
