import hashlib
import hmac
import json
import time
import unittest
from urllib.parse import urlencode

from app.errors import InvalidInitData
from app.security import AdminAccess, validate_init_data

TOKEN = "123456:TEST-TOKEN"


def sign(fields: dict, token: str = TOKEN) -> str:
    check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    return urlencode({**fields, "hash": hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()})


def fields(uid=42, age=0):
    return {"auth_date": str(int(time.time()) - age), "query_id": "AAA",
            "user": json.dumps({"id": uid, "first_name": "Аня", "username": "anya"}, ensure_ascii=False)}


class InitDataTest(unittest.TestCase):
    def test_valid(self):
        user = validate_init_data(sign(fields()), TOKEN)
        self.assertEqual(user["id"], 42)
        self.assertEqual(user["first_name"], "Аня")

    def test_tampered_user_id_rejected(self):
        raw = sign(fields(uid=42)).replace("%22id%22%3A+42", "%22id%22%3A+1")
        with self.assertRaises(InvalidInitData):
            validate_init_data(raw, TOKEN)

    def test_wrong_token_rejected(self):
        with self.assertRaises(InvalidInitData):
            validate_init_data(sign(fields(), token="999:OTHER"), TOKEN)

    def test_missing_hash_and_empty_rejected(self):
        for raw in ("", "auth_date=1&user=%7B%7D"):
            with self.assertRaises(InvalidInitData):
                validate_init_data(raw, TOKEN)

    def test_expired_rejected(self):
        with self.assertRaises(InvalidInitData):
            validate_init_data(sign(fields(age=90000)), TOKEN, max_age=86400)

    def test_no_bot_token_rejects_everything(self):
        with self.assertRaises(InvalidInitData):
            validate_init_data(sign(fields()), "")


class RolesTest(unittest.TestCase):
    def test_roles(self):
        a = AdminAccess(frozenset({1}), frozenset({2, 1}))
        self.assertEqual(a.roles(1), ["owner", "developer"])
        self.assertEqual(a.roles(2), ["developer"])
        self.assertEqual(a.roles(3), [])
