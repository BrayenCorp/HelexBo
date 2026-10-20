class _Pred:
    def __init__(self, fn, name="pred"):
        self.fn, self.name = fn, name

    def __call__(self, event):
        try:
            return bool(self.fn(event))
        except Exception:
            return False

    def __and__(self, other):
        return _Pred(lambda e: self(e) and other(e), f"{self.name}&{other.name}")

    def __or__(self, other):
        return _Pred(lambda e: self(e) or other(e), f"{self.name}|{other.name}")

    def __invert__(self):
        return _Pred(lambda e: not self(e), f"!{self.name}")


class _Field:
    def __init__(self, name):
        self.name = name

    def _get(self, event):
        return getattr(event, self.name, None)

    def __call__(self, event):  # просто наличие поля
        return bool(self._get(event))

    def __eq__(self, other):
        return _Pred(lambda e: self._get(e) == other, f"{self.name}=={other}")

    def startswith(self, prefix):
        return _Pred(lambda e: isinstance(self._get(e), str) and self._get(e).startswith(prefix), f"{self.name}^{prefix}")

    def in_(self, items):
        return _Pred(lambda e: self._get(e) in items, f"{self.name}in")

    def __and__(self, other):
        return _Pred(lambda e: bool(self._get(e)), self.name) & other

    def __invert__(self):
        return ~_Pred(lambda e: bool(self._get(e)), self.name)

    def __hash__(self):
        return hash(self.name)


class _Magic:
    def __getattr__(self, name):
        return _Field(name)


class Command:
    def __init__(self, *names, **kw):
        self.names = [n if isinstance(n, str) else getattr(n, "command", "") for n in names]

    def __call__(self, event):
        text = getattr(event, "text", "") or ""
        return any(text.split()[0].lstrip("/").split("@")[0] == n for n in self.names) if text.startswith("/") else False


class CommandStart:
    def __init__(self, **kw):
        pass

    def __call__(self, event):
        return (getattr(event, "text", "") or "").startswith("/start")
