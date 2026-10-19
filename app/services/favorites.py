"""Избранное: шаблоны и готовые результаты пользователя."""
from __future__ import annotations

from ..db import Database, now
from ..errors import DomainError
from . import orders, templates


def ids(db: Database, user_id: int) -> dict:
    with db.read() as conn:
        rows = conn.execute("SELECT kind, ref_id FROM favorites WHERE user_id = ? ORDER BY created_at DESC", (user_id,)).fetchall()
    return {"templates": [r["ref_id"] for r in rows if r["kind"] == "template"],
            "orders": [r["ref_id"] for r in rows if r["kind"] == "order"]}


def set_favorite(db: Database, user_id: int, kind: str, ref_id: int, on: bool) -> dict:
    if kind not in ("template", "order"):
        raise DomainError("Неизвестный тип избранного")
    with db.tx() as conn:
        if on:
            if kind == "template":
                ok = conn.execute("SELECT 1 FROM templates WHERE id = ? AND is_published = 1", (ref_id,)).fetchone()
            else:  # в избранное можно добавить только свой готовый результат
                ok = conn.execute(
                    "SELECT 1 FROM orders WHERE id = ? AND user_id = ? AND status = 'done' AND result_path IS NOT NULL",
                    (ref_id, user_id),
                ).fetchone()
            if ok is None:
                raise DomainError("Нельзя добавить в избранное", code="not_found", status=404)
            conn.execute("INSERT OR IGNORE INTO favorites (user_id, kind, ref_id, created_at) VALUES (?, ?, ?, ?)",
                         (user_id, kind, ref_id, now()))
        else:
            conn.execute("DELETE FROM favorites WHERE user_id = ? AND kind = ? AND ref_id = ?", (user_id, kind, ref_id))
    return ids(db, user_id)


def list_all(db: Database, user_id: int) -> dict:
    fav = ids(db, user_id)
    tpls = []
    for tid in fav["templates"]:
        try:
            tpls.append(templates.get_published(db, tid))
        except DomainError:
            continue  # шаблон сняли с публикации
    results = []
    for oid in fav["orders"]:
        o = orders.get_user_order(db, user_id, oid)
        if o and o["status"] == "done" and o["result_path"]:
            results.append(orders.public_order(o))
    return {"templates": tpls, "results": results}
