"""AI-модели в интерфейсе: название, описание, назначение, цена. Управляются из админки.

Модель в интерфейсе ссылается на provider_key — готовый провайдер из app/ai (image-default, video-default, ...).
Новая карточка модели добавляется без правки интерфейса; новый ПРОВАЙДЕР (подключение к реальному API)
пишется один раз в app/ai/external.py."""
from __future__ import annotations

from ..db import Database, now
from ..errors import DomainError
from .templates import KNOWN_MODELS


def _public(r: dict) -> dict:
    return {"id": r["id"], "name": r["name"], "kind": r["kind"], "description": r["description"], "purpose": r["purpose"],
            "audience": [a.strip() for a in r["audience"].split(",") if a.strip()], "image_url": r["image_url"],
            "price_credits": r["price_credits"]}


def public_list(db: Database, kind: str | None = None) -> list[dict]:
    sql, args = "SELECT * FROM ai_models WHERE is_active = 1", []
    if kind:
        sql += " AND kind = ?"; args.append(kind)
    with db.read() as conn:
        return [_public(dict(r)) for r in conn.execute(sql + " ORDER BY sort_order, id", args).fetchall()]


def admin_list(db: Database) -> list[dict]:
    with db.read() as conn:
        rows = conn.execute(
            "SELECT m.*, (SELECT COUNT(*) FROM orders o WHERE o.model_id = m.id) AS generations FROM ai_models m ORDER BY m.sort_order, m.id"
        ).fetchall()
    return [dict(r) for r in rows]


def _clean(fields: dict, partial: bool) -> dict:
    out: dict = {}
    for key, cap in (("name", 80), ("description", 400), ("purpose", 200), ("audience", 300), ("image_url", 500)):
        if key in fields:
            out[key] = str(fields[key]).strip()[:cap]
    if "name" in out and not out["name"]:
        raise DomainError("Название модели не может быть пустым")
    if "kind" in fields:
        if fields["kind"] not in ("photo", "video"):
            raise DomainError("Тип модели: photo или video")
        out["kind"] = fields["kind"]
    if "provider_key" in fields:
        if fields["provider_key"] not in KNOWN_MODELS:
            raise DomainError("Неизвестный провайдер. Доступны: " + ", ".join(KNOWN_MODELS))
        out["provider_key"] = fields["provider_key"]
    for key in ("price_credits", "sort_order"):
        if key in fields:
            try:
                out[key] = int(fields[key])
            except (TypeError, ValueError):
                raise DomainError("Цена и порядок должны быть числами")
    if out.get("price_credits", 0) < 0:
        raise DomainError("Цена не может быть отрицательной")
    if "is_active" in fields:
        out["is_active"] = 1 if fields["is_active"] in (True, 1, "1", "true") else 0
    if not partial:
        for need in ("name", "kind", "provider_key"):
            if need not in out:
                raise DomainError("Заполните название, тип и провайдера")
    return out


def create(db: Database, fields: dict) -> dict:
    data = _clean(fields, partial=False)
    cols = ["created_at", *data]
    with db.tx() as conn:
        cur = conn.execute(f"INSERT INTO ai_models ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})", [now(), *data.values()])
        return dict(conn.execute("SELECT * FROM ai_models WHERE id = ?", (cur.lastrowid,)).fetchone())


def update(db: Database, model_id: int, fields: dict) -> dict:
    data = _clean(fields, partial=True)
    with db.tx() as conn:
        if conn.execute("SELECT 1 FROM ai_models WHERE id = ?", (model_id,)).fetchone() is None:
            raise DomainError("Модель не найдена", code="not_found", status=404)
        if data:
            conn.execute(f"UPDATE ai_models SET {', '.join(f'{k} = ?' for k in data)} WHERE id = ?", [*data.values(), model_id])
        return dict(conn.execute("SELECT * FROM ai_models WHERE id = ?", (model_id,)).fetchone())


def delete(db: Database, model_id: int) -> dict:
    """Модель с историей генераций не удаляется (чтобы не потерять аналитику), а отключается."""
    with db.tx() as conn:
        if conn.execute("SELECT 1 FROM ai_models WHERE id = ?", (model_id,)).fetchone() is None:
            raise DomainError("Модель не найдена", code="not_found", status=404)
        used = conn.execute("SELECT COUNT(*) AS n FROM orders WHERE model_id = ?", (model_id,)).fetchone()["n"]
        if used:
            conn.execute("UPDATE ai_models SET is_active = 0 WHERE id = ?", (model_id,))
            return {"deleted": False, "hidden": True}
        conn.execute("DELETE FROM ai_models WHERE id = ?", (model_id,))
        return {"deleted": True, "hidden": False}


def get_active(conn, model_id: int, kind: str):
    row = conn.execute("SELECT * FROM ai_models WHERE id = ? AND is_active = 1", (model_id,)).fetchone()
    if row is None or row["kind"] != kind:
        raise DomainError("Эта модель недоступна — выберите другую", code="model_unavailable")
    return row
