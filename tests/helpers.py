import io
import tempfile
import unittest

from PIL import Image

from app.ai.registry import ProviderRegistry
from app.db import Database, init_db
from app.services import users
from app.storage import Storage


def make_photo(size=(200, 200), fmt="JPEG") -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, (200, 120, 90)).save(buf, fmt)
    return buf.getvalue()


class BaseTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = self._tmp.name
        self.db = Database(f"{self.dir}/test.db")
        init_db(self.db)
        with self.db.tx() as conn:  # старые тестовые пакеты (p10/p30/p100) нужны ряду проверок о кредитах и платежах
            conn.execute("UPDATE packages SET is_active = 1 WHERE id IN ('p10', 'p30', 'p100')")
        self.storage = Storage(self.dir)
        self.mock = ProviderRegistry("mock")
        self.live = ProviderRegistry("live")  # заглушки: ключей нет → «не подключено»
        users.upsert_user(self.db, 1, "kid_parent", "Анна")
        users.register(self.db, 1)  # вход через Telegram выполнен

    def add_balance(self, user_id, amount):
        from app.services import credits
        with self.db.tx() as conn:
            credits.apply(conn, user_id, amount, "test_grant")

    def tpl(self, kind="photo", price=None):
        with self.db.read() as conn:
            row = conn.execute("SELECT * FROM templates WHERE kind = ? AND is_published = 1 AND is_system = 0 ORDER BY id", (kind,)).fetchone()
        if price is not None:
            with self.db.tx() as conn:
                conn.execute("UPDATE templates SET price_credits = ? WHERE id = ?", (price, row["id"]))
        return row["id"]

    def submit(self, rid, template_id=None, user_id=1, source="bot", kind="photo"):
        from app.services import orders
        return orders.submit_generation(
            self.db, self.storage, user_id=user_id, template_id=template_id or self.tpl(kind),
            request_id=rid, image_bytes=make_photo(), source=source,
        )

    def balance_matches_ledger(self, user_id=1):
        with self.db.read() as conn:
            bal = conn.execute("SELECT balance FROM users WHERE tg_id = ?", (user_id,)).fetchone()["balance"]
            led = conn.execute("SELECT COALESCE(SUM(delta), 0) AS s FROM credit_ledger WHERE user_id = ?", (user_id,)).fetchone()["s"]
        return bal == led
