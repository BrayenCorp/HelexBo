"""Контент главной страницы и FAQ — редактируется в админке, ничего не зашито в интерфейс."""
from __future__ import annotations

import json

from ..db import Database
from ..errors import DomainError

DEFAULTS: dict = {
    "hero": {"title": "Создавай реальность без границ",
             "text": "Фото, видео и AI-инструменты для создания контента прямо внутри Telegram.",
             "primary": "Начать создавать", "secondary": "Узнать больше"},
    "capabilities": [
        {"title": "AI Фото", "text": "Создавай реалистичные изображения и фотографии."},
        {"title": "AI Видео", "text": "Создавай короткие AI-видео."},
        {"title": "AI Портреты", "text": "Создавай профессиональные портреты."},
        {"title": "Fashion", "text": "Создавай fashion-контент."},
        {"title": "Lifestyle", "text": "Создавай lifestyle-сцены."},
        {"title": "Тренды", "text": "Используй популярные AI-тренды."},
        {"title": "Редактирование", "text": "Изменяй существующие изображения."},
        {"title": "Создание похожего", "text": "Создавай новые варианты на основе результата."},
    ],
    "steps": [{"title": "Выбери идею", "text": ""}, {"title": "Выбери стиль или модель", "text": ""},
              {"title": "Запусти генерацию", "text": ""}, {"title": "Получи результат", "text": ""}],
    "why": [
        {"title": "Всё в одном месте", "text": "Фото, видео, тренды и AI-инструменты внутри одного Mini App."},
        {"title": "Быстро", "text": "Создавай контент без сложных программ."},
        {"title": "Постоянно обновляем", "text": "Добавляем новые модели, стили и тренды."},
        {"title": "Удобная система токенов", "text": "Платишь только за то, что используешь."},
        {"title": "Telegram", "text": "Не нужно создавать отдельный аккаунт и запоминать пароль."},
    ],
    "about": {"title": "О Nolla AI",
              "text": "Nolla AI — AI-платформа для создания визуального контента. Мы объединяем современные AI-модели, генерацию изображений, видео, редактирование и популярные тренды в одном удобном интерфейсе. Всё доступно прямо внутри Telegram."},
    "tokens": {"title": "Токены Nolla AI", "text": "Токены используются для создания AI-контента."},
    "payment": {"title": "Удобная оплата", "text": "Выбирайте удобный способ оплаты и пополняйте баланс за несколько секунд."},
    "cta": {"title": "Готов создать что-то своё?", "text": "Попробуй Nolla AI", "button": "Начать создавать"},
}
LISTS = {"capabilities": ("title", "text"), "steps": ("title", "text"), "why": ("title", "text")}
OBJECTS = {"hero": ("title", "text", "primary", "secondary"), "about": ("title", "text"), "tokens": ("title", "text"),
           "payment": ("title", "text"), "cta": ("title", "text", "button")}


def get_all(db: Database) -> dict:
    with db.read() as conn:
        rows = {r["key"]: r["value"] for r in conn.execute("SELECT key, value FROM settings WHERE key LIKE 'content_%'").fetchall()}
    out = {}
    for name, default in DEFAULTS.items():
        try:
            out[name] = json.loads(rows[f"content_{name}"]) if f"content_{name}" in rows else default
        except ValueError:
            out[name] = default
    return out


def update(db: Database, name: str, value) -> dict:
    if name in LISTS:
        if not isinstance(value, list) or len(value) > 20:
            raise DomainError("Нужен список (до 20 элементов)")
        fields = LISTS[name]
        clean = [{k: str(item.get(k, "")).strip()[:400] for k in fields} for item in value if isinstance(item, dict)]
        clean = [c for c in clean if c[fields[0]]]
    elif name in OBJECTS:
        if not isinstance(value, dict):
            raise DomainError("Некорректный блок")
        clean = {k: str(value.get(k, "")).strip()[:600] for k in OBJECTS[name]}
    else:
        raise DomainError("Неизвестный блок контента", code="not_found", status=404)
    with db.tx() as conn:
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (f"content_{name}", json.dumps(clean, ensure_ascii=False)))
    return get_all(db)


# ---------- FAQ ----------
def faq_public(db: Database) -> list[dict]:
    with db.read() as conn:
        rows = conn.execute("SELECT id, question, answer FROM faq WHERE is_active = 1 ORDER BY sort_order, id").fetchall()
    return [dict(r) for r in rows]


def faq_admin(db: Database) -> list[dict]:
    with db.read() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM faq ORDER BY sort_order, id").fetchall()]


def faq_save(db: Database, fields: dict, faq_id: int | None = None) -> dict:
    q, a = str(fields.get("question", "")).strip()[:300], str(fields.get("answer", "")).strip()[:2000]
    if faq_id is None and (not q or not a):
        raise DomainError("Заполните вопрос и ответ")
    with db.tx() as conn:
        if faq_id is None:
            cur = conn.execute("INSERT INTO faq (question, answer, sort_order, is_active) VALUES (?, ?, ?, ?)",
                               (q, a, int(fields.get("sort_order", 100)), 1 if fields.get("is_active", True) else 0))
            faq_id = cur.lastrowid
        else:
            if conn.execute("SELECT 1 FROM faq WHERE id = ?", (faq_id,)).fetchone() is None:
                raise DomainError("Вопрос не найден", code="not_found", status=404)
            sets, args = [], []
            if "question" in fields and q:
                sets.append("question = ?"); args.append(q)
            if "answer" in fields and a:
                sets.append("answer = ?"); args.append(a)
            if "sort_order" in fields:
                sets.append("sort_order = ?"); args.append(int(fields["sort_order"]))
            if "is_active" in fields:
                sets.append("is_active = ?"); args.append(1 if fields["is_active"] else 0)
            if sets:
                conn.execute(f"UPDATE faq SET {', '.join(sets)} WHERE id = ?", [*args, faq_id])
        return dict(conn.execute("SELECT * FROM faq WHERE id = ?", (faq_id,)).fetchone())


def faq_delete(db: Database, faq_id: int) -> None:
    with db.tx() as conn:
        conn.execute("DELETE FROM faq WHERE id = ?", (faq_id,))
