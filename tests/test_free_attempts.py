import threading

from app.db import Database
from app.services import generation, orders, users
from tests.helpers import BaseTest


class FreeAttemptsTest(BaseTest):
    def test_first_photo_free_second_paid(self):
        o1, _ = self.submit("a")
        self.assertEqual((o1["used_free"], o1["price_credits"]), (1, 0))
        self.add_balance(1, 5)
        o2, _ = self.submit("b")
        self.assertEqual(o2["used_free"], 0)
        self.assertGreater(o2["price_credits"], 0)
        self.assertTrue(self.balance_matches_ledger())

    def test_photo_and_video_have_separate_free_attempts(self):
        p, _ = self.submit("p", kind="photo")
        v, _ = self.submit("v", kind="video")
        self.assertEqual((p["used_free"], v["used_free"]), (1, 1))
        st = orders.free_status(self.db, 1)
        self.assertEqual(st, {"photo": False, "video": False})

    def test_free_attempt_not_burned_by_failed_generation(self):
        o, _ = self.submit("a")
        generation.process_order(self.db, self.storage, self.live, o["id"])  # провайдер не подключён → fail
        self.assertEqual(orders.get_order(self.db, o["id"])["status"], "failed")
        self.assertTrue(orders.free_status(self.db, 1)["photo"])
        o2, _ = self.submit("b")
        self.assertEqual(o2["used_free"], 1)

    def test_successful_generation_keeps_attempt_used(self):
        o, _ = self.submit("a")
        done = generation.process_order(self.db, self.storage, self.mock, o["id"])
        self.assertEqual(done["status"], "done")
        self.assertFalse(orders.free_status(self.db, 1)["photo"])

    def test_restart_does_not_reset_free_attempts(self):
        self.submit("a")
        reopened = Database(self.db.path)  # «перезапуск»: новое подключение к той же базе
        users.upsert_user(reopened, 1, "x", "Анна")
        self.assertFalse(orders.free_status(reopened, 1)["photo"])

    def test_bot_and_app_share_the_same_free_attempt(self):
        self.submit("tg:1:10", source="bot")
        with self.assertRaises(Exception):  # у пользователя нет кредитов — вторая (платная) попытка из Mini App невозможна
            self.submit("app-uuid-1", source="app")
        self.assertFalse(orders.free_status(self.db, 1)["photo"])

    def test_parallel_requests_give_only_one_free(self):
        self.add_balance(1, 50)
        results = []

        def worker(i):
            o, _ = self.submit(f"r{i}")
            results.append(o["used_free"])

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(6)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        self.assertEqual(sum(results), 1)
        self.assertEqual(len(results), 6)
        self.assertTrue(self.balance_matches_ledger())
