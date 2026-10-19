"""Заказы на генерацию — общая логика для бота и Mini App.

Правила:
* бесплатная попытка — одна на тип (фото/видео); занимается при создании заказа и
  освобождается, если генерация не удалась (индекс one_free_per_kind в БД);
* платный заказ списывает кредиты при создании и автоматически возвращает их при ошибке;
* повторный запрос с тем же request_id возвращает уже созданный заказ, ничего не списывая.
"""
from __future__ import annotations

import json
import sqlite3

from ..db import Database, now
from ..errors import DomainError, TemplateNotFound
from ..storage import Storage
from . import credits, models as models_service, params as params_service, site_settings, templates as tpl_service
from .images import sanitize_image

PUBLIC_FAIL_MESSAGE = "Не получилось создать результат. Бесплатная попытка и кредиты возвращены — попробуйте ещё раз позже."


def free_available(conn: sqlite3.Connection, user_id: int, kind: str) -> bool:
    if kind not in ("photo", "video"):  # бесплатная попытка — только на фото и видео
        return False
    row = conn.execute(
        "SELECT 1 FROM orders WHERE user_id = ? AND kind = ? AND used_free = 1 "
        "AND status IN ('created', 'processing', 'done') LIMIT 1",
        (user_id, kind),
    ).fetchone()
    return row is None


def free_status(db: Database, user_id: int) -> dict:
    with db.read() as conn:
        return {k: free_available(conn, user_id, k) for k in ("photo", "video")}


def _get(conn: sqlite3.Connection, order_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    return dict(row) if row else None


def get_order(db: Database, order_id: int) -> dict | None:
    with db.read() as conn:
        return _get(conn, order_id)


IMAGE_MATERIALS = {"photo", "person", "garment", "product"}


def _check_materials(tpl, has_img: bool, has_img2: bool, prompt: str, has_avatar: bool) -> None:
    """Проверка, что у инструмента есть всё нужное (фото, одежда, идея). Сообщения — на русском."""
    try:
        req = json.loads(tpl["required"] or "[]")
    except (ValueError, TypeError):
        req = []
    if "avatar" in req:
        if not has_avatar:
            raise DomainError("Выберите готовый аватар", code="avatar_required")
        return
    if "person" in req and "garment" in req:  # примерка
        if not has_img:
            raise DomainError("Загрузите фотографию человека", code="photo_required")
        if not has_img2:
            raise DomainError("Загрузите изображение одежды", code="garment_required")
        return
    need_img = [m for m in req if m in IMAGE_MATERIALS]
    if need_img and not has_img and not ("idea" in req and prompt):
        raise DomainError("Загрузите изображение" + (" или опишите идею" if "idea" in req else ""), code="photo_required")
    if req == ["idea"] and not prompt and not has_img:
        raise DomainError("Опишите идею", code="empty_request")


def _check_model_input(model, has_img: bool) -> None:
    try:
        tags = json.loads(model["tags"] or "[]")
    except (ValueError, TypeError):
        tags = []
    if "in:text" in tags and has_img:
        raise DomainError("Эта модель не поддерживает данный формат: она создаёт видео только по тексту", code="unsupported_input")
    if "in:image" in tags and not has_img:
        raise DomainError("Для этой модели загрузите исходное изображение", code="photo_required")


def _own_result_image(db: Database, user_id: int, order_id: int) -> bytes:
    with db.read() as conn:
        row = conn.execute("SELECT status, result_path, result_mime FROM orders WHERE id = ? AND user_id = ?", (order_id, user_id)).fetchone()
    if row is None or row["status"] != "done" or not row["result_path"]:
        raise DomainError("Работа не найдена или ещё не готова", code="order_not_found", status=404)
    if not (row["result_mime"] or "").startswith("image/jpeg"):
        raise DomainError("Как референс можно использовать только изображение", code="unsupported_input")
    from pathlib import Path
    try:
        return Path(row["result_path"]).read_bytes()
    except OSError:
        raise DomainError("Файл работы удалён", code="result_not_found", status=404)


def submit_generation(
    db: Database,
    storage: Storage,
    *,
    user_id: int,
    request_id: str,
    source: str,
    template_id: int | None = None,
    kind: str | None = None,
    image_bytes: bytes | None = None,
    prompt: str = "",
    params: dict | str | None = None,
    max_bytes: int = 10 * 1024 * 1024,
    style: str | None = None,
    model_id: int | None = None,
    image2_bytes: bytes | None = None,
    avatar_id: int | None = None,
    ref_order_id: int | None = None,
) -> tuple[dict, bool]:
    """Создать заказ. Возвращает (заказ, создан_ли_новый). Цена берётся только из БД.

    Два режима: по шаблону (template_id) и «свободный» (template_id=None, нужен kind и описание
    или фото). Фото необязательно в обоих режимах.
    """
    if not request_id or len(request_id) > 128:
        raise DomainError("Некорректный идентификатор запроса", code="bad_request")

    with db.read() as conn:
        row = conn.execute(
            "SELECT * FROM orders WHERE user_id = ? AND request_id = ?", (user_id, request_id)
        ).fetchone()
    if row:
        return dict(row), False

    if template_id is None and kind not in ("photo", "video", "audio"):
        raise DomainError("Укажите, что создаём: изображение, видео или аудио", code="bad_request")
    prompt = params_service.clean_prompt(prompt, params_service.MAX_AUDIO_TEXT if kind == "audio" else params_service.MAX_PROMPT)
    clean_params = params_service.clean_params(params)

    if ref_order_id and not image_bytes:  # «использовать как референс / изменить / оживить»: берём результат своей работы
        image_bytes = _own_result_image(db, user_id, ref_order_id)
    path: str | None = None
    path2: str | None = None
    if image_bytes:
        path = storage.save_upload(sanitize_image(image_bytes, max_bytes))
    if image2_bytes:
        path2 = storage.save_upload(sanitize_image(image2_bytes, max_bytes))
    existing: dict | None = None
    try:
        with db.tx() as conn:
            row = conn.execute(
                "SELECT * FROM orders WHERE user_id = ? AND request_id = ?", (user_id, request_id)
            ).fetchone()
            if row:
                existing = dict(row)
            else:
                user = conn.execute("SELECT status, registered_at FROM users WHERE tg_id = ?", (user_id,)).fetchone()
                if user is None:
                    raise DomainError("Пользователь не найден", code="unknown_user", status=404)
                if user["status"] == "blocked":
                    raise DomainError("Аккаунт заблокирован. Обратитесь в поддержку.", code="blocked", status=403)
                if not user["registered_at"]:
                    raise DomainError("Сначала войдите в Nolla AI через Telegram", code="registration_required", status=403)
                if template_id is None:
                    tpl = tpl_service.get_system(conn, kind)
                    if tpl is None or not tpl["is_published"]:
                        raise DomainError("Создание сейчас отключено", code="freeform_disabled", status=503)
                    if kind == "audio":
                        if not prompt:
                            raise DomainError("Введите текст для озвучки", code="empty_request")
                        if path or path2:
                            raise DomainError("Эта модель не поддерживает данный формат: для аудио нужен только текст", code="unsupported_input")
                    elif not prompt and not path:
                        raise DomainError("Опишите, что хотите получить, или загрузите изображение", code="empty_request")
                else:
                    tpl = conn.execute(
                        "SELECT * FROM templates WHERE id = ? AND is_published = 1 AND is_system = 0", (template_id,)
                    ).fetchone()
                    if tpl is None:
                        raise TemplateNotFound()
                avatar = None
                if avatar_id:
                    avatar = conn.execute("SELECT * FROM avatars WHERE id = ? AND user_id = ?", (avatar_id, user_id)).fetchone()
                    if avatar is None or avatar["status"] != "ready":
                        raise DomainError("Аватар не найден или ещё не готов", code="avatar_unavailable")
                _check_materials(tpl, bool(path), bool(path2), prompt, avatar is not None)
                base_price, model_key, used_model_id = tpl["price_credits"], None, None
                if template_id is None and model_id:
                    m = models_service.get_active(conn, model_id, tpl["kind"])
                    _check_model_input(m, bool(path))
                    base_price, model_key, used_model_id = m["price_credits"], m["provider_key"], m["id"]
                style_id, _ = tpl_service.resolve_style(tpl["styles"], style)
                use_free = free_available(conn, user_id, tpl["kind"])
                price = 0 if use_free else base_price
                cur = conn.execute(
                    "INSERT INTO orders (user_id, template_id, kind, status, used_free, price_credits, "
                    "source, request_id, style, prompt, params, model, model_id, input_path, input2_path, avatar_id, created_at) "
                    "VALUES (?, ?, ?, 'created', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (user_id, tpl["id"], tpl["kind"], int(use_free), price, source, request_id, style_id, prompt,
                     json.dumps(clean_params, ensure_ascii=False), model_key, used_model_id, path, path2, avatar["id"] if avatar else None, now()),
                )
                order_id = cur.lastrowid
                if price > 0:
                    credits.apply(conn, user_id, -price, "order_charge", order_id=order_id)
                order = _get(conn, order_id)
    except BaseException:
        storage.delete(path)
        storage.delete(path2)
        raise
    if existing is not None:
        storage.delete(path)
        storage.delete(path2)
        return existing, False
    return order, True


def quote(db: Database, user_id: int, *, template_id: int | None, kind: str | None, model_id: int | None) -> dict:
    """Сколько будет стоить одна генерация и бесплатна ли она для пользователя (для проверки баланса и экрана «Стоимость»)."""
    with db.read() as conn:
        if template_id is None:
            tpl = tpl_service.get_system(conn, kind) if kind in ("photo", "video", "audio") else None
        else:
            tpl = conn.execute("SELECT * FROM templates WHERE id = ? AND is_published = 1 AND is_system = 0", (template_id,)).fetchone()
        if tpl is None:
            raise TemplateNotFound()
        base = tpl["price_credits"]
        if template_id is None and model_id:
            base = models_service.get_active(conn, model_id, tpl["kind"])["price_credits"]
        return {"base": base, "free": free_available(conn, user_id, tpl["kind"]), "kind": tpl["kind"]}


def submit_variants(db: Database, storage: Storage, *, count: int, request_id: str, **kw) -> list[tuple[dict, bool]]:
    """Несколько вариантов за один запрос: каждый — отдельный заказ со своим списанием и возвратом при ошибке.
    Баланс проверяется заранее на всю сумму, чтобы не создавать половину заказов."""
    with db.read() as conn:
        limit = site_settings.get_int(conn, "max_variants", 4)
    count = max(1, min(int(count or 1), limit))
    with db.read() as conn:  # повтор уже принятого запроса не проверяем по балансу — он ничего не спишет
        repeat = conn.execute("SELECT 1 FROM orders WHERE user_id = ? AND request_id = ?", (kw["user_id"], request_id)).fetchone()
    if count > 1 and not repeat:
        q = quote(db, kw["user_id"], template_id=kw.get("template_id"), kind=kw.get("kind"), model_id=kw.get("model_id"))
        total = (0 if q["free"] else q["base"]) + q["base"] * (count - 1)
        with db.read() as conn:
            row = conn.execute("SELECT balance FROM users WHERE tg_id = ?", (kw["user_id"],)).fetchone()
        if row is not None and row["balance"] < total:
            from ..errors import InsufficientCredits
            raise InsufficientCredits(total, row["balance"])
    return [submit_generation(db, storage, request_id=request_id if i == 0 else f"{request_id}#{i}", **kw) for i in range(count)]


def claim_for_processing(db: Database, order_id: int) -> dict | None:
    """Атомарно перевести created → processing. Второй вызов вернёт None — двойной обработки не будет."""
    with db.tx() as conn:
        cur = conn.execute(
            "UPDATE orders SET status = 'processing', started_at = ? WHERE id = ? AND status = 'created'",
            (now(), order_id),
        )
        if cur.rowcount == 0:
            return None
        return _get(conn, order_id)


def complete_order(
    db: Database, order_id: int, *, result_path: str, mime: str, provider: str, cost_usd: float, is_stub: bool,
    duration_sec: int | None = None, frames: list | None = None,
) -> bool:
    with db.tx() as conn:
        cur = conn.execute(
            "UPDATE orders SET status = 'done', result_path = ?, result_mime = ?, provider = ?, "
            "provider_cost_usd = ?, is_stub = ?, duration_sec = ?, frames = ?, finished_at = ? WHERE id = ? AND status = 'processing'",
            (result_path, mime, provider, cost_usd, int(is_stub), duration_sec, json.dumps(frames or [], ensure_ascii=False), now(), order_id),
        )
        return cur.rowcount == 1


def set_stage(db: Database, order_id: int, stage: str) -> None:
    """Этап, о котором сообщил провайдер (creating / processing / almost). Процентов не выдумываем."""
    with db.tx() as conn:
        conn.execute("UPDATE orders SET stage = ? WHERE id = ? AND status IN ('created', 'processing')", (stage, order_id))


def fail_order(
    db: Database, order_id: int, error: str, public_message: str = PUBLIC_FAIL_MESSAGE, source: str = "generation",
    error_type: str = "unknown", severity: str = "error",
) -> bool:
    """Пометить заказ проваленным и вернуть токены. Повторный вызов ничего не делает."""
    with db.tx() as conn:
        cur = conn.execute(
            "UPDATE orders SET status = 'failed', error = ?, error_public = ?, finished_at = ? "
            "WHERE id = ? AND status IN ('created', 'processing')",
            (error[:2000], public_message, now(), order_id),
        )
        if cur.rowcount == 0:
            return False
        row = conn.execute(
            "SELECT o.user_id, o.price_credits, COALESCE(o.model, t.model) AS provider FROM orders o "
            "JOIN templates t ON t.id = o.template_id WHERE o.id = ?", (order_id,)).fetchone()
        if row["price_credits"] > 0:
            credits.apply(conn, row["user_id"], row["price_credits"], "order_refund", order_id=order_id)
        conn.execute(
            "INSERT INTO error_log (created_at, source, order_id, message, user_id, provider, error_type, severity) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (now(), source, order_id, error[:2000], row["user_id"], row["provider"], error_type, severity),
        )
        return True


def fail_unfinished_orders(db: Database, reason: str) -> int:
    """При старте: заказы, зависшие после перезапуска, закрываются с возвратом кредитов."""
    with db.read() as conn:
        ids = [r["id"] for r in conn.execute("SELECT id FROM orders WHERE status IN ('created', 'processing')")]
    return sum(1 for i in ids if fail_order(db, i, reason, source="startup", error_type="restart", severity="warning"))


def _loads(raw) -> dict:
    try:
        return json.loads(raw or "{}")
    except ValueError:
        return {}


def public_order(o: dict) -> dict:
    return {
        "id": o["id"], "template_id": o["template_id"], "kind": o["kind"], "status": o["status"],
        "used_free": bool(o["used_free"]), "price_credits": o["price_credits"],
        "has_result": o["status"] == "done" and bool(o.get("result_path")),
        "result_mime": o.get("result_mime"), "is_stub": bool(o.get("is_stub")),
        "error": o.get("error_public") if o["status"] == "failed" else None,
        "created_at": o["created_at"], "title": o.get("title"), "emoji": o.get("emoji"),
        "preview_url": o.get("preview_url") or "",
        "prompt": o.get("prompt") or "", "params": _loads(o.get("params")), "style": o.get("style"),
        "duration_sec": o.get("duration_sec"), "template_id": o["template_id"], "is_system": bool(o.get("is_system")),
        "stage": o.get("stage"), "section": o.get("section") or "legacy", "tool": o.get("tool") or "", "model_name": o.get("model_name"),
        "group": order_group(o), "frames": [f["label"] for f in _frames(o)], "avatar_id": o.get("avatar_id"),
    }


def order_group(o: dict) -> str:
    """Раздел истории: audio / video / effects / avatars / marketing / images."""
    if o["kind"] in ("audio", "video"):
        return o["kind"]
    sec = o.get("section") or "legacy"
    return {"effect": "effects", "avatar": "avatars", "marketing": "marketing", "mtool": "marketing"}.get(sec, "images")


def _frames(o: dict) -> list[dict]:
    try:
        data = json.loads(o.get("frames") or "[]")
    except ValueError:
        return []
    return [f for f in data if isinstance(f, dict) and f.get("path")]


def frame_path(o: dict, index: int) -> str | None:
    fr = _frames(o)
    return fr[index]["path"] if 0 <= index < len(fr) else None


def list_user_orders(db: Database, user_id: int, limit: int = 50) -> list[dict]:
    with db.read() as conn:
        rows = conn.execute(
            "SELECT o.*, t.title AS title, t.emoji AS emoji, t.preview_url AS preview_url, t.is_system AS is_system, t.section AS section, t.tool AS tool, m.name AS model_name FROM orders o "
            "JOIN templates t ON t.id = o.template_id LEFT JOIN ai_models m ON m.id = o.model_id WHERE o.user_id = ? AND o.is_hidden = 0 ORDER BY o.id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def get_user_order(db: Database, user_id: int, order_id: int) -> dict | None:
    with db.read() as conn:
        row = conn.execute(
            "SELECT o.*, t.title AS title, t.emoji AS emoji, t.preview_url AS preview_url, t.is_system AS is_system, t.section AS section, t.tool AS tool, m.name AS model_name FROM orders o "
            "JOIN templates t ON t.id = o.template_id LEFT JOIN ai_models m ON m.id = o.model_id WHERE o.id = ? AND o.user_id = ?",
            (order_id, user_id),
        ).fetchone()
    return dict(row) if row else None


def clear_input(db: Database, storage: Storage, order_id: int) -> None:
    """Исходное фото человека после обработки не нужно — удаляем его сразу."""
    with db.tx() as conn:
        row = conn.execute("SELECT input_path, input2_path FROM orders WHERE id = ?", (order_id,)).fetchone()
        conn.execute("UPDATE orders SET input_path = NULL, input2_path = NULL WHERE id = ?", (order_id,))
    if row:
        storage.delete(row["input_path"])
        storage.delete(row["input2_path"])


def delete_user_media(db: Database, storage: Storage, user_id: int) -> int:
    """«Удалить мои работы и фото»: стираем файлы завершённых заказов. Историю заказов и баланс не трогаем."""
    with db.tx() as conn:
        rows = conn.execute(
            "SELECT input_path, input2_path, result_path, frames FROM orders WHERE user_id = ? AND status IN ('done', 'failed')", (user_id,)
        ).fetchall()
        conn.execute(
            "UPDATE orders SET input_path = NULL, input2_path = NULL, result_path = NULL, result_mime = NULL, frames = '[]' "
            "WHERE user_id = ? AND status IN ('done', 'failed')", (user_id,)
        )
        conn.execute("DELETE FROM favorites WHERE user_id = ? AND kind = 'order'", (user_id,))
    count = 0
    for r in rows:
        for path in (r["input_path"], r["input2_path"], r["result_path"], *[f["path"] for f in _frames(dict(r))]):
            if path:
                storage.delete(path)
                count += 1
    return count


def count_done(db: Database, user_id: int) -> int:
    with db.read() as conn:
        return conn.execute("SELECT COUNT(*) AS n FROM orders WHERE user_id = ? AND status = 'done'", (user_id,)).fetchone()["n"]


def count_done_by_kind(db: Database, user_id: int) -> dict:
    with db.read() as conn:
        rows = conn.execute("SELECT kind, COUNT(*) AS n FROM orders WHERE user_id = ? AND status = 'done' GROUP BY kind", (user_id,)).fetchall()
    out = {"photo": 0, "video": 0, "audio": 0}
    out.update({r["kind"]: r["n"] for r in rows})
    return out


def delete_order(db: Database, storage: Storage, user_id: int, order_id: int) -> None:
    """«Удалить» в истории: стираем файлы и убираем работу из списка. Запись о заказе остаётся (кредиты, статистика)."""
    with db.tx() as conn:
        row = conn.execute("SELECT status, input_path, result_path, frames FROM orders WHERE id = ? AND user_id = ?", (order_id, user_id)).fetchone()
        if row is None:
            raise DomainError("Работа не найдена", code="order_not_found", status=404)
        if row["status"] in ("created", "processing"):
            raise DomainError("Работа ещё создаётся — подождите завершения", code="order_busy", status=409)
        conn.execute("UPDATE orders SET is_hidden = 1, input_path = NULL, result_path = NULL, result_mime = NULL, frames = '[]' WHERE id = ?", (order_id,))
        conn.execute("DELETE FROM favorites WHERE user_id = ? AND kind = 'order' AND ref_id = ?", (user_id, order_id))
    storage.delete(row["input_path"])
    storage.delete(row["result_path"])
    for f in _frames(dict(row)):
        storage.delete(f["path"])
