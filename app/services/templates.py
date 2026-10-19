"""Шаблоны (образы): читаются из БД, поэтому владелец меняет их в админ-панели без правки кода."""
from __future__ import annotations

import json
import re
import uuid

from ..db import Database, now
from .. import catalog_data as cd
from ..errors import DomainError, TemplateNotFound

KINDS = ("photo", "video", "audio")
KNOWN_MODELS = ("image-default", "video-default", "audio-default", "seedance-2.5")
EDITABLE = (
    "title", "description", "category", "kind", "model", "prompt", "preview_url",
    "emoji", "price_credits", "is_published", "is_popular", "is_trend", "sort_order", "style_label",
    "section", "tag", "tool", "required", "supported_models",
)
MAX_STYLES = 8
MAX_EXAMPLES = 8


def media_kind(url: str) -> str:
    return "video" if url.lower().split("?")[0].endswith((".mp4", ".webm", ".mov")) else "image"


# ---------- стили (раздел «Параметры» при создании) ----------

def parse_styles(raw: str | None) -> list[dict]:
    try:
        data = json.loads(raw or "[]")
    except ValueError:
        return []
    return [s for s in data if isinstance(s, dict) and s.get("id") and s.get("title")] if isinstance(data, list) else []


def clean_styles(value) -> list[dict]:
    if not isinstance(value, list):
        raise DomainError("Стили должны быть списком")
    if len(value) > MAX_STYLES:
        raise DomainError(f"Не больше {MAX_STYLES} стилей")
    out, used = [], set()
    for i, item in enumerate(value):
        if not isinstance(item, dict):
            raise DomainError("Некорректный стиль")
        title = str(item.get("title", "")).strip()
        if not title:
            raise DomainError("У каждого стиля должно быть название")
        sid = re.sub(r"[^a-z0-9_-]", "", str(item.get("id", "")).lower()) or f"s{i + 1}"
        while sid in used:
            sid += "x"
        used.add(sid)
        out.append({"id": sid, "title": title[:40], "prompt": str(item.get("prompt", "")).strip()[:300]})
    return out


def resolve_style(styles_raw: str | None, style_id: str | None) -> tuple[str | None, str]:
    """(id стиля, дополнение к промпту). Если стилей нет — (None, "")."""
    styles = parse_styles(styles_raw)
    if not styles:
        return None, ""
    if style_id is None:
        return styles[0]["id"], styles[0]["prompt"]
    for s in styles:
        if s["id"] == style_id:
            return s["id"], s["prompt"]
    raise DomainError("Такого стиля нет — выберите стиль из списка", code="unknown_style")


# ---------- публичная часть ----------

def public(t: dict) -> dict:
    """Клиенту отдаём только то, что нужно для показа. Промпт и модель — внутренние."""
    return {
        "id": t["id"], "title": t["title"], "description": t["description"],
        "category": t["category"], "kind": t["kind"], "preview_url": t["preview_url"],
        "preview_kind": media_kind(t["preview_url"]),
        "emoji": t["emoji"], "price_credits": t["price_credits"],
        "is_popular": bool(t["is_popular"]), "is_trend": bool(t["is_trend"]),
        "style_label": t.get("style_label", ""),
    }


def list_published(
    db: Database, kind: str | None = None, category: str | None = None,
    q: str | None = None, collection: str | None = None, limit: int | None = None,
) -> list[dict]:
    sql = "SELECT * FROM templates WHERE is_published = 1 AND is_system = 0"
    args: list = []
    if kind:
        sql += " AND kind = ?"
        args.append(kind)
    if category:
        sql += " AND category = ?"
        args.append(category)
    if collection == "popular":
        sql += " AND is_popular = 1"
    elif collection == "trend":
        sql += " AND is_trend = 1"
    sql += " ORDER BY created_at DESC, id DESC" if collection == "new" else " ORDER BY sort_order, id"
    with db.read() as conn:
        rows = [dict(r) for r in conn.execute(sql, args).fetchall()]
    if q:
        needle = q.strip().casefold()
        rows = [r for r in rows if needle in r["title"].casefold() or needle in r["description"].casefold()]
    if collection == "new":
        rows = rows[: limit or 24]
    elif limit:
        rows = rows[:limit]
    return [public(r) for r in rows]


def list_flagged(db: Database, flag: str, limit: int = 12) -> list[dict]:
    """Подборки для главной: flag — is_popular или is_trend."""
    if flag not in ("is_popular", "is_trend"):
        raise ValueError(flag)
    with db.read() as conn:
        rows = conn.execute(
            f"SELECT * FROM templates WHERE is_published = 1 AND is_system = 0 AND {flag} = 1 ORDER BY sort_order, id LIMIT ?", (limit,)
        ).fetchall()
    return [public(dict(r)) for r in rows]


def list_examples(db: Database, template_id: int) -> list[dict]:
    with db.read() as conn:
        rows = conn.execute(
            "SELECT media_url FROM template_examples WHERE template_id = ? ORDER BY sort_order, id", (template_id,)
        ).fetchall()
    return [{"url": r["media_url"], "kind": media_kind(r["media_url"])} for r in rows]


def get_published(db: Database, template_id: int) -> dict:
    with db.read() as conn:
        row = conn.execute("SELECT * FROM templates WHERE id = ? AND is_published = 1 AND is_system = 0", (template_id,)).fetchone()
    if row is None:
        raise TemplateNotFound()
    t = dict(row)
    out = public(t)
    out["examples"] = list_examples(db, template_id)
    out["styles"] = [{"id": s["id"], "title": s["title"]} for s in parse_styles(t["styles"])]
    return out


# ---------- админка ----------

def admin_list(db: Database) -> list[dict]:
    with db.read() as conn:
        rows = conn.execute("SELECT * FROM templates WHERE is_system = 0 ORDER BY sort_order, id").fetchall()
    return [dict(r) for r in rows]


def admin_get(db: Database, template_id: int) -> dict:
    with db.read() as conn:
        row = conn.execute("SELECT * FROM templates WHERE id = ?", (template_id,)).fetchone()
    if row is None:
        raise DomainError("Шаблон не найден", code="template_not_found", status=404)
    t = dict(row)
    t["styles"] = parse_styles(t["styles"])
    t["examples"] = [e["url"] for e in list_examples(db, template_id)]
    return t


def _clean(fields: dict, partial: bool) -> dict:
    out: dict = {}
    for key in EDITABLE:
        if key not in fields:
            continue
        val = fields[key]
        if key in ("title", "description", "category", "kind", "model", "prompt", "preview_url", "emoji", "style_label"):
            val = str(val).strip()
        if key in ("price_credits", "sort_order"):
            try:
                val = int(val)
            except (TypeError, ValueError):
                raise DomainError(f"Поле {key} должно быть числом")
        if key in ("is_published", "is_popular", "is_trend"):
            val = 1 if val in (True, 1, "1", "true", "True") else 0
        if key in ("section", "tag", "tool"):
            val = str(val or "").strip()
        if key in ("required", "supported_models"):
            if isinstance(val, str):
                try:
                    val = json.loads(val or "[]")
                except ValueError:
                    raise DomainError(f"Поле {key}: ожидается список")
            if not isinstance(val, list) or any(not isinstance(x, str) for x in val):
                raise DomainError(f"Поле {key}: ожидается список строк")
            val = json.dumps([x.strip() for x in val if x.strip()], ensure_ascii=False)
        out[key] = val
    if "section" in out and out["section"] not in ("legacy", *cd.SECTIONS):
        raise DomainError("Неизвестный раздел платформы")
    if "styles" in fields:
        out["styles"] = json.dumps(clean_styles(fields["styles"]), ensure_ascii=False)
    if "title" in out and not out["title"]:
        raise DomainError("Название не может быть пустым")
    if "kind" in out and out["kind"] not in KINDS:
        raise DomainError("Тип генерации: photo, video или audio")
    if "price_credits" in out and out["price_credits"] < 0:
        raise DomainError("Цена не может быть отрицательной")
    if not partial:
        for need in ("title", "kind"):
            if need not in out:
                raise DomainError(f"Не заполнено поле {need}")
    return out


def _clean_examples(value) -> list[str]:
    if not isinstance(value, list):
        raise DomainError("Примеры должны быть списком")
    urls = [str(u).strip() for u in value if str(u).strip()]
    if len(urls) > MAX_EXAMPLES:
        raise DomainError(f"Не больше {MAX_EXAMPLES} примеров")
    for u in urls:
        if not (u.startswith("/media/") or u.startswith("https://")):
            raise DomainError("Примеры: загрузите файл или укажите https-ссылку")
    return urls


def _check_category(conn, category: str) -> None:
    if conn.execute("SELECT 1 FROM categories WHERE id = ?", (category,)).fetchone() is None:
        raise DomainError("Такой категории нет — выберите категорию из списка")


def _save_examples(conn, template_id: int, urls: list[str]) -> None:
    conn.execute("DELETE FROM template_examples WHERE template_id = ?", (template_id,))
    for i, u in enumerate(urls):
        conn.execute("INSERT INTO template_examples (template_id, media_url, sort_order) VALUES (?, ?, ?)", (template_id, u, i))


def create(db: Database, fields: dict) -> dict:
    data = _clean(fields, partial=False)
    examples = _clean_examples(fields["examples"]) if "examples" in fields else None
    data.setdefault("model", {"photo": "image-default", "video": "video-default", "audio": "audio-default"}[data["kind"]])
    ts = now()
    with db.tx() as conn:
        if "category" not in data:
            first = conn.execute("SELECT id FROM categories ORDER BY sort_order LIMIT 1").fetchone()
            if first is None:
                raise DomainError("Сначала создайте хотя бы одну категорию")
            data["category"] = first["id"]
        _check_category(conn, data["category"])
        cols = ["slug", "created_at", "updated_at", *data.keys()]
        vals = [f"t-{uuid.uuid4().hex[:8]}", ts, ts, *data.values()]
        cur = conn.execute(f"INSERT INTO templates ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})", vals)
        if examples is not None:
            _save_examples(conn, cur.lastrowid, examples)
        row = conn.execute("SELECT * FROM templates WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


def update(db: Database, template_id: int, fields: dict) -> dict:
    data = _clean(fields, partial=True)
    examples = _clean_examples(fields["examples"]) if "examples" in fields else None
    with db.tx() as conn:
        if conn.execute("SELECT 1 FROM templates WHERE id = ?", (template_id,)).fetchone() is None:
            raise DomainError("Шаблон не найден", code="template_not_found", status=404)
        if "category" in data:
            _check_category(conn, data["category"])
        if data:
            sets = ", ".join(f"{k} = ?" for k in data) + ", updated_at = ?"
            conn.execute(f"UPDATE templates SET {sets} WHERE id = ?", [*data.values(), now(), template_id])
        if examples is not None:
            _save_examples(conn, template_id, examples)
        row = conn.execute("SELECT * FROM templates WHERE id = ?", (template_id,)).fetchone()
    return dict(row)


def delete(db: Database, template_id: int) -> dict:
    """Удаляет шаблон. Если по нему уже были заказы — удалять нельзя (история и возвраты),
    поэтому он скрывается с публикации. Ссылки с витрины и из избранного снимаются."""
    with db.tx() as conn:
        if conn.execute("SELECT 1 FROM templates WHERE id = ?", (template_id,)).fetchone() is None:
            raise DomainError("Шаблон не найден", code="template_not_found", status=404)
        used = conn.execute("SELECT COUNT(*) AS n FROM orders WHERE template_id = ?", (template_id,)).fetchone()["n"]
        if used:
            conn.execute("UPDATE templates SET is_published = 0, is_popular = 0, is_trend = 0, updated_at = ? WHERE id = ?",
                         (now(), template_id))
            return {"deleted": False, "hidden": True, "orders": used}
        conn.execute("DELETE FROM favorites WHERE kind = 'template' AND ref_id = ?", (template_id,))
        conn.execute("DELETE FROM templates WHERE id = ?", (template_id,))
        return {"deleted": True, "hidden": False, "orders": 0}


# ---------- свободная генерация (скрытые системные шаблоны) ----------

def get_system(conn, kind: str):
    """Системный шаблон «свободного» фото/видео. Возвращает строку или None."""
    return conn.execute("SELECT * FROM templates WHERE is_system = 1 AND kind = ? LIMIT 1", (kind,)).fetchone()


def list_system(db: Database) -> list[dict]:
    with db.read() as conn:
        rows = conn.execute("SELECT id, kind, title, model, price_credits, is_published FROM templates WHERE is_system = 1 ORDER BY kind").fetchall()
    return [{**dict(r), "enabled": bool(r["is_published"])} for r in rows]


def update_system(db: Database, kind: str, fields: dict) -> dict:
    sets, args = [], []
    if "price_credits" in fields:
        try:
            price = int(fields["price_credits"])
        except (TypeError, ValueError):
            raise DomainError("Цена должна быть числом")
        if price < 0:
            raise DomainError("Цена не может быть отрицательной")
        sets.append("price_credits = ?"); args.append(price)
    if "model" in fields:
        if fields["model"] not in KNOWN_MODELS:
            raise DomainError("Неизвестная модель")
        sets.append("model = ?"); args.append(fields["model"])
    if "enabled" in fields:
        sets.append("is_published = ?"); args.append(1 if fields["enabled"] in (True, 1, "1", "true") else 0)
    with db.tx() as conn:
        if get_system(conn, kind) is None:
            raise DomainError("Системный шаблон не найден", code="not_found", status=404)
        if sets:
            conn.execute(f"UPDATE templates SET {', '.join(sets)}, updated_at = ? WHERE is_system = 1 AND kind = ?", [*args, now(), kind])
    return next(x for x in list_system(db) if x["kind"] == kind)
