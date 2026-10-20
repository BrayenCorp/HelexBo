"""SQLite: схема и транзакции. Бот и Mini App работают с одной и той же базой."""
from __future__ import annotations

import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    tg_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    balance INTEGER NOT NULL DEFAULT 0 CHECK (balance >= 0),
    notify_chat INTEGER NOT NULL DEFAULT 1,
    is_pro INTEGER NOT NULL DEFAULT 0,
    last_name TEXT,
    language_code TEXT,
    photo_url TEXT,
    source TEXT,
    campaign TEXT,
    material TEXT,
    referrer_id INTEGER,
    status TEXT NOT NULL DEFAULT 'active',
    registered_at TEXT,
    welcomed INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    last_seen_at TEXT
);

CREATE TABLE IF NOT EXISTS templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT 'cartoon',
    kind TEXT NOT NULL CHECK (kind IN ('photo', 'video', 'audio')),
    model TEXT NOT NULL DEFAULT 'image-default',
    prompt TEXT NOT NULL DEFAULT '',
    preview_url TEXT NOT NULL DEFAULT '',
    emoji TEXT NOT NULL DEFAULT '✨',
    price_credits INTEGER NOT NULL DEFAULT 1 CHECK (price_credits >= 0),
    is_published INTEGER NOT NULL DEFAULT 0,
    is_popular INTEGER NOT NULL DEFAULT 0,
    is_trend INTEGER NOT NULL DEFAULT 0,
    styles TEXT NOT NULL DEFAULT '[]',
    style_label TEXT NOT NULL DEFAULT '',
    is_system INTEGER NOT NULL DEFAULT 0,
    sort_order INTEGER NOT NULL DEFAULT 100,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(tg_id),
    template_id INTEGER NOT NULL REFERENCES templates(id),
    kind TEXT NOT NULL CHECK (kind IN ('photo', 'video', 'audio')),
    status TEXT NOT NULL CHECK (status IN ('created', 'processing', 'done', 'failed')),
    used_free INTEGER NOT NULL DEFAULT 0,
    price_credits INTEGER NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'bot',
    request_id TEXT NOT NULL,
    style TEXT,
    prompt TEXT NOT NULL DEFAULT '',
    params TEXT NOT NULL DEFAULT '{}',
    duration_sec INTEGER,
    is_hidden INTEGER NOT NULL DEFAULT 0,
    model TEXT,
    model_id INTEGER,
    input_path TEXT,
    result_path TEXT,
    result_mime TEXT,
    provider TEXT,
    provider_cost_usd REAL NOT NULL DEFAULT 0,
    is_stub INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    error_public TEXT,
    created_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    UNIQUE (user_id, request_id)
);

-- Одна бесплатная генерация каждого типа на пользователя. Провалившаяся не считается.
CREATE UNIQUE INDEX IF NOT EXISTS one_free_per_kind
    ON orders (user_id, kind)
    WHERE used_free = 1 AND status IN ('created', 'processing', 'done');

CREATE TABLE IF NOT EXISTS credit_ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(tg_id),
    delta INTEGER NOT NULL,
    reason TEXT NOT NULL,
    order_id INTEGER REFERENCES orders(id),
    payment_id INTEGER REFERENCES payments(id),
    note TEXT,
    created_at TEXT NOT NULL
);

-- Защита от повторного списания/возврата/начисления.
CREATE UNIQUE INDEX IF NOT EXISTS ledger_once_per_order
    ON credit_ledger (order_id, reason) WHERE order_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS ledger_once_per_payment
    ON credit_ledger (payment_id, reason) WHERE payment_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS packages (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    credits INTEGER NOT NULL CHECK (credits > 0),
    price_stars INTEGER NOT NULL CHECK (price_stars > 0),
    badge TEXT NOT NULL DEFAULT '',
    bonus INTEGER NOT NULL DEFAULT 0,
    old_price_stars INTEGER,
    price_rub INTEGER,
    is_active INTEGER NOT NULL DEFAULT 1,
    sort_order INTEGER NOT NULL DEFAULT 100
);

CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(tg_id),
    package_id TEXT NOT NULL REFERENCES packages(id),
    credits INTEGER NOT NULL,
    bonus INTEGER NOT NULL DEFAULT 0,
    amount_stars INTEGER NOT NULL,
    amount REAL NOT NULL DEFAULT 0,
    currency TEXT NOT NULL DEFAULT 'XTR',
    provider TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'paid', 'failed', 'refunded', 'cancelled')),
    payload TEXT NOT NULL UNIQUE,
    provider_charge_id TEXT UNIQUE,
    created_at TEXT NOT NULL,
    paid_at TEXT
);

CREATE TABLE IF NOT EXISTS categories (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    cover_url TEXT NOT NULL DEFAULT '',
    sort_order INTEGER NOT NULL DEFAULT 100,
    is_published INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

-- Витрина: примеры работ студии (фото и видео), которые владелец загружает сам.
CREATE TABLE IF NOT EXISTS showcase (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL DEFAULT '',
    media_url TEXT NOT NULL,
    prompt TEXT NOT NULL DEFAULT '',
    template_id INTEGER REFERENCES templates(id) ON DELETE SET NULL,
    sort_order INTEGER NOT NULL DEFAULT 100,
    is_published INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

-- Избранное: шаблоны и готовые результаты пользователя.
CREATE TABLE IF NOT EXISTS favorites (
    user_id INTEGER NOT NULL REFERENCES users(tg_id),
    kind TEXT NOT NULL CHECK (kind IN ('template', 'order')),
    ref_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (user_id, kind, ref_id)
);

-- Примеры результата на странице образа (фото/видео, загружает владелец).
CREATE TABLE IF NOT EXISTS template_examples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id INTEGER NOT NULL REFERENCES templates(id) ON DELETE CASCADE,
    media_url TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 100
);

-- События продукта: то, чего нет в других таблицах (старт бота, открытие Mini App, команды, действия админов).
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    user_id INTEGER,
    name TEXT NOT NULL,
    props TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS events_name_idx ON events (name, ts);
CREATE INDEX IF NOT EXISTS events_user_idx ON events (user_id, ts);

-- Активность по дням: основа для DAU/WAU/MAU, удержания и «вернувшихся».
CREATE TABLE IF NOT EXISTS daily_activity (
    day TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    PRIMARY KEY (day, user_id)
);

CREATE TABLE IF NOT EXISTS admin_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    admin_id INTEGER NOT NULL,
    admin_name TEXT NOT NULL DEFAULT '',
    action TEXT NOT NULL,
    target_user_id INTEGER,
    before TEXT,
    after TEXT,
    note TEXT NOT NULL DEFAULT ''
);

-- AI-модели для пользователя: название, описание, цена. provider_key — ключ провайдера из app/ai.
CREATE TABLE IF NOT EXISTS ai_models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('photo', 'video', 'audio')),
    description TEXT NOT NULL DEFAULT '',
    purpose TEXT NOT NULL DEFAULT '',
    audience TEXT NOT NULL DEFAULT '',
    image_url TEXT NOT NULL DEFAULT '',
    provider_key TEXT NOT NULL,
    price_credits INTEGER NOT NULL DEFAULT 2 CHECK (price_credits >= 0),
    is_active INTEGER NOT NULL DEFAULT 0,
    sort_order INTEGER NOT NULL DEFAULT 100,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS faq (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 100,
    is_active INTEGER NOT NULL DEFAULT 1
);

-- Способы оплаты: статус задаёт админ, доступность пользователю дополнительно зависит от подключения.
CREATE TABLE IF NOT EXISTS payment_methods (
    code TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'off' CHECK (status IN ('on', 'soon', 'off')),
    fee_percent REAL,
    sort_order INTEGER NOT NULL DEFAULT 100
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS error_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    source TEXT NOT NULL,
    order_id INTEGER,
    message TEXT NOT NULL,
    user_id INTEGER,
    provider TEXT,
    error_type TEXT,
    severity TEXT NOT NULL DEFAULT 'error'
);

-- Аватары пользователя: фото хранятся на диске, запись — только метаданные и статус.
CREATE TABLE IF NOT EXISTS avatars (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(tg_id),
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'analyzing', 'creating', 'ready', 'failed')),
    photo_count INTEGER NOT NULL DEFAULT 0,
    photos TEXT NOT NULL DEFAULT '[]',
    cover_path TEXT,
    error TEXT,
    is_stub INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    ready_at TEXT
);

-- Личные токены для подключения MCP-клиентов. Хранится только хеш: сам токен показывается один раз.
CREATE TABLE IF NOT EXISTS api_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(tg_id),
    token_hash TEXT NOT NULL UNIQUE,
    label TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    last_used_at TEXT,
    revoked_at TEXT
);

CREATE INDEX IF NOT EXISTS orders_user_idx ON orders (user_id, id DESC);
CREATE INDEX IF NOT EXISTS ledger_user_idx ON credit_ledger (user_id, id DESC);
CREATE INDEX IF NOT EXISTS orders_created_idx ON orders (created_at);
CREATE INDEX IF NOT EXISTS users_created_idx ON users (created_at);
CREATE INDEX IF NOT EXISTS payments_paid_idx ON payments (paid_at);
CREATE INDEX IF NOT EXISTS activity_user_idx ON daily_activity (user_id, day);
CREATE INDEX IF NOT EXISTS examples_tpl_idx ON template_examples (template_id, sort_order);
CREATE INDEX IF NOT EXISTS avatars_user_idx ON avatars (user_id, id DESC);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Database:
    """Каждая операция открывает своё соединение — безопасно для потоков."""

    def __init__(self, path: str):
        self.path = path
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    @contextmanager
    def read(self) -> Iterator[sqlite3.Connection]:
        conn = self.connect()
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def tx(self) -> Iterator[sqlite3.Connection]:
        """Запись: BEGIN IMMEDIATE сериализует конкурирующие операции (баланс, бесплатные попытки)."""
        conn = self.connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
            except BaseException:
                conn.execute("ROLLBACK")
                raise
            else:
                conn.execute("COMMIT")
        finally:
            conn.close()


def _rebuild_payments(conn: sqlite3.Connection) -> None:
    """Старая таблица платежей жёстко допускала только test/stars. Пересобираем без этого ограничения,
    чтобы СБП, карты и другие способы можно было подключить без новой миграции. Данные сохраняются."""
    row = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'payments'").fetchone()
    if row is None or "CHECK (provider" not in row["sql"]:
        return
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(payments)")}
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        conn.executescript("""
        BEGIN;
        CREATE TABLE payments_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(tg_id),
            package_id TEXT NOT NULL REFERENCES packages(id),
            credits INTEGER NOT NULL,
            bonus INTEGER NOT NULL DEFAULT 0,
            amount_stars INTEGER NOT NULL,
            amount REAL NOT NULL DEFAULT 0,
            currency TEXT NOT NULL DEFAULT 'XTR',
            provider TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('pending', 'paid', 'failed', 'refunded', 'cancelled')),
            payload TEXT NOT NULL UNIQUE,
            provider_charge_id TEXT UNIQUE,
            created_at TEXT NOT NULL,
            paid_at TEXT
        );
        INSERT INTO payments_new (id, user_id, package_id, credits, amount_stars, amount, provider, status, payload, provider_charge_id, created_at, paid_at)
            SELECT id, user_id, package_id, credits, amount_stars, amount_stars, provider, status, payload, provider_charge_id, created_at, paid_at FROM payments;
        DROP TABLE payments;
        ALTER TABLE payments_new RENAME TO payments;
        COMMIT;
        """)
    finally:
        conn.execute("PRAGMA foreign_keys = ON")
    del cols


def _rebuild_table(conn: sqlite3.Connection, table: str, old: str, new: str) -> None:
    """Пересобирает таблицу с изменённым текстом схемы (SQLite не умеет менять CHECK на месте).
    Порядок из документации SQLite: новая таблица → копирование → удаление старой → переименование → индексы."""
    row = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)).fetchone()
    if row is None or old not in row["sql"]:
        return
    ddl = row["sql"].replace(old, new)
    ddl = re.sub(r'CREATE TABLE\s+(IF NOT EXISTS\s+)?"?%s"?' % table, f"CREATE TABLE {table}__new", ddl, count=1)
    indexes = [r["sql"] for r in conn.execute("SELECT sql FROM sqlite_master WHERE type = 'index' AND tbl_name = ? AND sql IS NOT NULL", (table,))]
    cols = ", ".join(r["name"] for r in conn.execute(f"PRAGMA table_info({table})"))
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        conn.execute("BEGIN")
        try:
            conn.execute(ddl)
            conn.execute(f"INSERT INTO {table}__new ({cols}) SELECT {cols} FROM {table}")
            conn.execute(f"DROP TABLE {table}")
            conn.execute(f"ALTER TABLE {table}__new RENAME TO {table}")
            for sql in indexes:
                conn.execute(sql)
            bad = conn.execute("PRAGMA foreign_key_check").fetchall()
            if bad:
                raise sqlite3.IntegrityError(f"foreign_key_check после пересборки {table}: {len(bad)} нарушений")
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")


def _allow_audio(conn: sqlite3.Connection) -> None:
    """Старые базы допускали только photo/video. Добавляем 'audio' (данные сохраняются)."""
    old, new = "CHECK (kind IN ('photo', 'video'))", "CHECK (kind IN ('photo', 'video', 'audio'))"
    for table in ("templates", "orders", "ai_models"):
        _rebuild_table(conn, table, old, new)


def _backfill_users(conn: sqlite3.Connection) -> None:
    """Один раз при обновлении: пользователи, созданные раньше, считаются уже зарегистрированными и приветствие
    не увидят; их известные даты активности (регистрация и последний вход) заносятся в daily_activity."""
    if conn.execute("SELECT 1 FROM settings WHERE key = 'registration_v5'").fetchone():
        return
    conn.execute("UPDATE users SET registered_at = created_at, welcomed = 1 WHERE registered_at IS NULL")
    conn.execute("INSERT OR IGNORE INTO daily_activity (day, user_id) SELECT substr(created_at, 1, 10), tg_id FROM users WHERE created_at IS NOT NULL")
    conn.execute("INSERT OR IGNORE INTO daily_activity (day, user_id) SELECT substr(last_seen_at, 1, 10), tg_id FROM users WHERE last_seen_at IS NOT NULL")
    conn.execute("INSERT INTO settings (key, value) VALUES ('registration_v5', '1')")


def _migrate(conn: sqlite3.Connection) -> None:
    """Дописывает то, чего нет в базе, созданной старой версией (данные не трогаются)."""
    def add(table: str, column: str, ddl: str) -> None:
        cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
        if column not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")

    add("templates", "is_trend", "INTEGER NOT NULL DEFAULT 0")
    add("templates", "styles", "TEXT NOT NULL DEFAULT '[]'")
    add("orders", "style", "TEXT")
    add("users", "notify_chat", "INTEGER NOT NULL DEFAULT 1")
    add("users", "is_pro", "INTEGER NOT NULL DEFAULT 0")
    add("templates", "style_label", "TEXT NOT NULL DEFAULT ''")
    add("templates", "is_system", "INTEGER NOT NULL DEFAULT 0")
    add("orders", "prompt", "TEXT NOT NULL DEFAULT ''")
    add("orders", "params", "TEXT NOT NULL DEFAULT '{}'")
    add("orders", "duration_sec", "INTEGER")
    add("orders", "is_hidden", "INTEGER NOT NULL DEFAULT 0")
    add("showcase", "prompt", "TEXT NOT NULL DEFAULT ''")
    for col, ddl in (("last_name", "TEXT"), ("language_code", "TEXT"), ("photo_url", "TEXT"), ("source", "TEXT"), ("campaign", "TEXT"),
                     ("material", "TEXT"), ("referrer_id", "INTEGER"), ("status", "TEXT NOT NULL DEFAULT 'active'"),
                     ("registered_at", "TEXT"), ("welcomed", "INTEGER NOT NULL DEFAULT 0")):
        add("users", col, ddl)
    add("orders", "model", "TEXT")
    add("orders", "model_id", "INTEGER")
    add("packages", "bonus", "INTEGER NOT NULL DEFAULT 0")
    add("packages", "old_price_stars", "INTEGER")
    add("packages", "price_rub", "INTEGER")
    for col, ddl in (("user_id", "INTEGER"), ("provider", "TEXT"), ("error_type", "TEXT"), ("severity", "TEXT NOT NULL DEFAULT 'error'")):
        add("error_log", col, ddl)
    _rebuild_payments(conn)
    _backfill_users(conn)
    add("categories", "description", "TEXT NOT NULL DEFAULT ''")
    add("packages", "badge", "TEXT NOT NULL DEFAULT ''")
    # --- платформа: разделы каталога, аудио, аватары, интеграции ---
    add("templates", "section", "TEXT NOT NULL DEFAULT 'legacy'")  # legacy | idea | effect | trend | photoshoot | prompt | marketing | avatar
    add("templates", "tag", "TEXT NOT NULL DEFAULT ''")  # категория внутри раздела
    add("templates", "tool", "TEXT NOT NULL DEFAULT ''")  # особый инструмент: storyboard | angles | tryon | ...
    add("templates", "required", "TEXT NOT NULL DEFAULT '[]'")  # какие материалы нужны (photo, photo2, text, ...)
    add("templates", "supported_models", "TEXT NOT NULL DEFAULT '[]'")
    add("templates", "on_home", "INTEGER NOT NULL DEFAULT 1")   # показывать на главной
    add("templates", "on_ideas", "INTEGER NOT NULL DEFAULT 1")  # показывать в разделе «Идеи»
    add("ai_models", "slug", "TEXT NOT NULL DEFAULT ''")
    add("ai_models", "tags", "TEXT NOT NULL DEFAULT '[]'")  # категории моделей: photoreal, art, edit, fast, hq, new, t2v ...
    add("orders", "input2_path", "TEXT")  # второе изображение: референс, одежда
    add("orders", "frames", "TEXT NOT NULL DEFAULT '[]'")  # кадры раскадровки / ракурсы
    add("orders", "stage", "TEXT")  # этап, о котором сообщил провайдер
    add("orders", "avatar_id", "INTEGER")
    add("users", "prefs", "TEXT NOT NULL DEFAULT '{}'")
    add("payments", "demo_method", "TEXT")
    _allow_audio(conn)


def init_db(db: Database, seed: bool = True) -> None:
    with db.read() as conn:
        conn.executescript(SCHEMA)
        _migrate(conn)
    if seed:
        from .seed import seed_defaults

        seed_defaults(db)
