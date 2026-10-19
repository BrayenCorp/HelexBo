from app.errors import DomainError, DuplicateOperation, InsufficientCredits
from app.services import credits, orders, payments
from tests.helpers import BaseTest


class CreditsTest(BaseTest):
    def test_paid_order_charges_template_price_from_db(self):
        self.submit("free")  # занимаем бесплатную
        self.add_balance(1, 10)
        tid = self.tpl(price=3)
        o, _ = self.submit("paid", template_id=tid)
        self.assertEqual(o["price_credits"], 3)
        self.assertEqual(credits.get_balance(self.db, 1), 7)

    def test_insufficient_credits_blocks_and_changes_nothing(self):
        self.submit("free")
        tid = self.tpl(price=5)
        with self.assertRaises(InsufficientCredits):
            self.submit("paid", template_id=tid)
        self.assertEqual(credits.get_balance(self.db, 1), 0)
        self.assertEqual(len(orders.list_user_orders(self.db, 1)), 1)  # заказ не создался

    def test_repeat_request_does_not_charge_twice(self):
        self.submit("free")
        self.add_balance(1, 10)
        tid = self.tpl(price=4)
        a, created_a = self.submit("same", template_id=tid)
        b, created_b = self.submit("same", template_id=tid)  # обновление страницы / повтор запроса
        self.assertEqual((created_a, created_b), (True, False))
        self.assertEqual(a["id"], b["id"])
        self.assertEqual(credits.get_balance(self.db, 1), 6)

    def test_refund_on_failure_is_automatic_and_only_once(self):
        self.submit("free")
        self.add_balance(1, 10)
        tid = self.tpl(price=4)
        o, _ = self.submit("paid", template_id=tid)
        self.assertEqual(credits.get_balance(self.db, 1), 6)
        self.assertTrue(orders.fail_order(self.db, o["id"], "boom"))
        self.assertFalse(orders.fail_order(self.db, o["id"], "boom again"))
        self.assertEqual(credits.get_balance(self.db, 1), 10)
        self.assertTrue(self.balance_matches_ledger())

    def test_ledger_unique_index_blocks_duplicate_refund(self):
        self.add_balance(1, 5)
        self.submit("free")
        o, _ = self.submit("paid", template_id=self.tpl(price=2))
        with self.assertRaises(DuplicateOperation):
            with self.db.tx() as conn:
                credits.apply(conn, 1, -2, "order_charge", order_id=o["id"])
        self.assertTrue(self.balance_matches_ledger())

    def test_negative_balance_impossible(self):
        with self.assertRaises(InsufficientCredits):
            with self.db.tx() as conn:
                credits.apply(conn, 1, -1, "x")


class PaymentsTest(BaseTest):
    def test_credits_added_only_after_confirmation(self):
        p = payments.create_payment(self.db, 1, "p10", "test")
        self.assertEqual(credits.get_balance(self.db, 1), 0)
        pay, credited = payments.confirm_payment(self.db, p["payload"], provider="test", user_id=1)
        self.assertTrue(credited)
        self.assertEqual(credits.get_balance(self.db, 1), 10)
        self.assertEqual(pay["status"], "paid")

    def test_double_confirmation_does_not_double_credit(self):
        p = payments.create_payment(self.db, 1, "p30", "test")
        payments.confirm_payment(self.db, p["payload"], provider="test")
        _, credited = payments.confirm_payment(self.db, p["payload"], provider="test")
        self.assertFalse(credited)
        self.assertEqual(credits.get_balance(self.db, 1), 30)
        self.assertTrue(self.balance_matches_ledger())

    def test_stars_amount_mismatch_rejected(self):
        p = payments.create_payment(self.db, 1, "p10", "stars")
        with self.assertRaises(DomainError):
            payments.confirm_payment(self.db, p["payload"], provider="stars", provider_charge_id="c1", paid_stars=1)
        self.assertEqual(credits.get_balance(self.db, 1), 0)

    def test_stars_payment_credited_once_by_charge_id(self):
        p = payments.create_payment(self.db, 1, "p10", "stars")
        payments.confirm_payment(self.db, p["payload"], provider="stars", provider_charge_id="c1", paid_stars=p["amount_stars"])
        payments.confirm_payment(self.db, p["payload"], provider="stars", provider_charge_id="c1", paid_stars=p["amount_stars"])
        self.assertEqual(credits.get_balance(self.db, 1), 10)

    def test_same_charge_id_cannot_pay_two_payments(self):
        a = payments.create_payment(self.db, 1, "p10", "stars")
        b = payments.create_payment(self.db, 1, "p10", "stars")
        payments.confirm_payment(self.db, a["payload"], provider="stars", provider_charge_id="dup", paid_stars=a["amount_stars"])
        with self.assertRaises(DuplicateOperation):
            payments.confirm_payment(self.db, b["payload"], provider="stars", provider_charge_id="dup", paid_stars=b["amount_stars"])
        self.assertEqual(credits.get_balance(self.db, 1), 10)

    def test_provider_must_match(self):
        p = payments.create_payment(self.db, 1, "p10", "stars")
        with self.assertRaises(DomainError):
            payments.confirm_payment(self.db, p["payload"], provider="test")  # тестовой кнопкой Stars-платёж не закрыть
        self.assertEqual(credits.get_balance(self.db, 1), 0)

    def test_other_user_cannot_confirm(self):
        p = payments.create_payment(self.db, 1, "p10", "test")
        with self.assertRaises(DomainError):
            payments.confirm_payment(self.db, p["payload"], provider="test", user_id=2)
