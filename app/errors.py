"""Понятные доменные ошибки. API превращает их в JSON, бот — в сообщения."""
from __future__ import annotations


class DomainError(Exception):
    status = 400
    code = "error"

    def __init__(self, message: str, *, code: str | None = None, status: int | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        if status:
            self.status = status


class TemplateNotFound(DomainError):
    status = 404
    code = "template_not_found"

    def __init__(self):
        super().__init__("Шаблон не найден или снят с публикации")


class InsufficientCredits(DomainError):
    status = 402
    code = "insufficient_credits"

    def __init__(self, needed: int, balance: int):
        super().__init__(f"Недостаточно кредитов: нужно {needed}, на балансе {balance}")
        self.needed = needed
        self.balance = balance


class DuplicateOperation(DomainError):
    status = 409
    code = "duplicate_operation"


class InvalidImage(DomainError):
    code = "invalid_image"


class InvalidInitData(DomainError):
    status = 401
    code = "invalid_init_data"


class Forbidden(DomainError):
    status = 403
    code = "forbidden"
