"""Маленькая заглушка aiogram 3 — только чтобы тесты могли импортировать и прогонять бота."""
from .filters import _Magic

F = _Magic()


class BaseMiddleware:
    async def __call__(self, handler, event, data):
        return await handler(event, data)


class Bot:
    def __init__(self, token=None, **kw):
        self.token = token
        self.sent = []

    async def _send(self, kind, chat_id, payload=None, **kw):
        self.sent.append({"kind": kind, "chat_id": chat_id, "payload": payload, **kw})

    async def download(self, file_id, destination=None):
        data = getattr(self, "files", {}).get(file_id, b"")
        if destination is not None and hasattr(destination, "write"):
            destination.write(data)
        return data

    def __getattr__(self, name):
        if name.startswith("send_"):
            async def f(chat_id, payload=None, **kw):
                await self._send(name[5:], chat_id, payload, **kw)
            return f
        if name.startswith(("set_", "get_", "download")):
            async def f(*a, **kw):
                return None
            return f
        raise AttributeError(name)


class _Section:
    """Точка регистрации обработчиков: @router.message(...) / @router.callback_query(...)."""

    def __init__(self):
        self.handlers = []
        self.middlewares = []

    def __call__(self, *filters):
        def deco(fn):
            self.handlers.append((list(filters), fn))
            return fn
        return deco

    def outer_middleware(self, mw):
        self.middlewares.append(mw)
        return mw

    middleware = outer_middleware


class Router:
    def __init__(self, name=None):
        self.name = name
        self.message = _Section()
        self.callback_query = _Section()
        self.pre_checkout_query = _Section()

    def include_router(self, r):
        pass


class Dispatcher:
    def __init__(self, storage=None, **kw):
        self.storage = storage
        self.data = dict(kw)
        self.routers = []

    def include_router(self, r):
        self.routers.append(r)
