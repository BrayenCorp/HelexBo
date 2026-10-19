"""Тесты HTTP-слоя. Нужны fastapi и httpx (pip install -r requirements.txt); без них пропускаются."""
import json
import tempfile
import time
import unittest
from urllib.parse import urlencode
import hashlib, hmac

try:
    from fastapi.testclient import TestClient
    HAS_API = True
except Exception:  # pragma: no cover
    HAS_API = False

from tests.helpers import make_photo

TOKEN = "123456:TEST-TOKEN"


def init_data(uid: int) -> str:
    fields = {"auth_date": str(int(time.time())), "user": json.dumps({"id": uid, "first_name": "Аня"}, ensure_ascii=False)}
    check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", TOKEN.encode(), hashlib.sha256).digest()
    return urlencode({**fields, "hash": hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()})


@unittest.skipUnless(HAS_API, "fastapi/httpx не установлены")
class ApiTest(unittest.TestCase):
    def setUp(self):
        from app.ai.registry import ProviderRegistry
        from app.api import create_app
        from app.config import Settings
        from app.context import AppContext
        from app.db import Database, init_db
        from app.runner import Runner
        from app.security import AdminAccess
        from app.storage import Storage

        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        d = self._tmp.name
        s = Settings(bot_token=TOKEN, data_dir=d, database_path=f"{d}/t.db", webapp_dist=f"{d}/none",
                     owner_ids=frozenset({100}), ai_mode="mock", payments_mode="test")
        db = Database(s.database_path)
        init_db(db)
        providers = ProviderRegistry("mock")
        storage = Storage(d)
        ctx = AppContext(s, db, storage, providers, Runner(db, storage, providers), AdminAccess(s.owner_ids, s.developer_ids))
        self.client = TestClient(create_app(ctx))
        self.client.__enter__()
        self.addCleanup(lambda: self.client.__exit__(None, None, None))

    def h(self, uid=7):
        return {"Authorization": f"tma {init_data(uid)}"}

    def test_requires_valid_telegram_signature(self):
        self.assertEqual(self.client.get("/api/me").status_code, 401)
        self.assertEqual(self.client.get("/api/me", headers={"Authorization": "tma auth_date=1&hash=bad"}).status_code, 401)
        self.assertEqual(self.client.get("/api/me", headers={"X-Dev-User": "7"}).status_code, 401)  # DEV_MODE выключен
        r = self.client.get("/api/me", headers=self.h())
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["free"], {"photo": True, "video": True})

    def test_order_flow_and_free_attempt(self):
        tid = self.client.get("/api/templates?kind=photo", headers=self.h()).json()[0]["id"]
        files = {"photo": ("a.jpg", make_photo(), "image/jpeg")}
        r = self.client.post("/api/orders", headers=self.h(), data={"template_id": tid, "request_id": "r1"}, files=files)
        self.assertEqual(r.status_code, 200, r.text)
        oid = r.json()["order"]["id"]
        self.assertTrue(r.json()["order"]["used_free"])
        for _ in range(50):
            o = self.client.get(f"/api/orders/{oid}", headers=self.h()).json()
            if o["status"] in ("done", "failed"):
                break
            time.sleep(0.1)
        self.assertEqual(o["status"], "done")
        self.assertTrue(o["is_stub"])
        self.assertEqual(self.client.get(f"/api/orders/{oid}/result", headers=self.h()).status_code, 200)
        self.assertEqual(self.client.get(f"/api/orders/{oid}/result", headers=self.h(8)).status_code, 404)  # чужой заказ
        self.assertFalse(self.client.get("/api/me", headers=self.h()).json()["free"]["photo"])
        # повтор запроса с тем же request_id — тот же заказ, ничего нового
        again = self.client.post("/api/orders", headers=self.h(), data={"template_id": tid, "request_id": "r1"}, files=files).json()
        self.assertFalse(again["created"])
        # второе фото платное, а кредитов нет
        r2 = self.client.post("/api/orders", headers=self.h(), data={"template_id": tid, "request_id": "r2"}, files=files)
        self.assertEqual(r2.status_code, 402)

    def test_test_payment_and_admin_access(self):
        pay = self.client.post("/api/payments/start", headers=self.h(), json={"package_id": "p10"}).json()
        self.assertEqual(pay["mode"], "test")
        r = self.client.post("/api/payments/test-confirm", headers=self.h(), json={"payload": pay["payload"]}).json()
        self.assertEqual(r["balance"], 10)
        again = self.client.post("/api/payments/test-confirm", headers=self.h(), json={"payload": pay["payload"]}).json()
        self.assertEqual(again["balance"], 10)
        self.assertEqual(self.client.get("/api/admin/overview", headers=self.h(7)).status_code, 403)
        self.assertEqual(self.client.get("/api/admin/overview", headers=self.h(100)).status_code, 200)
        self.assertEqual(self.client.get("/api/admin/dev/errors", headers=self.h(100)).status_code, 403)  # у владельца нет роли разработчика
