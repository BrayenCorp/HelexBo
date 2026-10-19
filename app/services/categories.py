"""Категории каталога: название, обложка (фото или видео), порядок. Меняются в админ-панели."""
from __future__ import annotations

import uuid

from ..db import Database, now
from ..errors import DomainError


def list_public(db: Database) -> list[dict]:
    with db.read() as conn:
        rows = conn.execute(
            "SELECT c.id, c.title, c.description, c.cover_url, "
            "(SELECT COUNT(*) FROM templates t WHERE t.category = c.id AND t.is_published = 1) AS count "
            "FROM categories c WHERE c.is_published = 1 ORDER BY c.sort_order, c.created_at"
        ).fetchall()
    return [dict(r) for r in rows]


def get_public(db: Database, category_id: str) -> dict:
    for c in list_public(db):
        if c["id"] == category_id:
            return c
    raise DomainError("Категория не найдена", code="category_not_found", status=404)


def admin_list(db: Database) -> list[dict]:
    with db.read() as conn:
        rows = conn.execute(
            "SELECT c.*, (SELECT COUNT(*) FROM templates t WHERE t.category = c.id) AS templates_count "
            "FROM categories c ORDER BY c.sort_order, c.created_at"
        ).fetchall()
    return [dict(r) for r in rows]


def _clean(fields: dict, partial: bool) -> dict:
    out: dict = {}
    if "title" in fields:
        out["title"] = str(fields["title"]).strip()
        if not out["title"]:
            raise DomainError("Название не может быть пустым")
    elif not partial:
        raise DomainError("Укажите название категории")
    if "description" in fields:
        out["description"] = str(fields["description"]).strip()[:400]
    if "cover_url" in fields:
        out["cover_url"] = str(fields["cover_url"]).strip()
    if "sort_order" in fields:
        try:
            out["sort_order"] = int(fields["sort_order"])
        except (TypeError, ValueError):
            raise DomainError("Порядок должен быть числом")
    if "is_published" in fields:
        out["is_published"] = 1 if fields["is_published"] in (True, 1, "1", "true", "True") else 0
    return out


def create(db: Database, fields: dict) -> dict:
    data = _clean(fields, partial=False)
    cid = f"c-{uuid.uuid4().hex[:8]}"
    cols = ["id", "created_at", *data.keys()]
    with db.tx() as conn:
        conn.execute(f"INSERT INTO categories ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                     [cid, now(), *data.values()])
        return dict(conn.execute("SELECT * FROM categories WHERE id = ?", (cid,)).fetchone())


def update(db: Database, category_id: str, fields: dict) -> dict:
    data = _clean(fields, partial=True)
    with db.tx() as conn:
        if conn.execute("SELECT 1 FROM categories WHERE id = ?", (category_id,)).fetchone() is None:
            raise DomainError("Категория не найдена", code="category_not_found", status=404)
        if data:
            conn.execute(f"UPDATE categories SET {', '.join(f'{k} = ?' for k in data)} WHERE id = ?",
                         [*data.values(), category_id])
        return dict(conn.execute("SELECT * FROM categories WHERE id = ?", (category_id,)).fetchone())


def delete(db: Database, category_id: str) -> None:
    with db.tx() as conn:
        n = conn.execute("SELECT COUNT(*) AS n FROM templates WHERE category = ?", (category_id,)).fetchone()["n"]
        if n:
            raise DomainError(
                f"В категории {n} шаблонов. Перенесите или удалите их, либо просто снимите категорию с публикации.",
                code="category_not_empty", status=409,
            )
        conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
