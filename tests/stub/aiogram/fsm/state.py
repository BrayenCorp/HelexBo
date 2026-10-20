class State:
    def __init__(self, name=None):
        self._name = name

    def __set_name__(self, owner, name):
        self._name = f"{owner.__name__}:{name}"

    def __str__(self):
        return self._name or "state"

    def __call__(self, event):  # как фильтр состояния
        return True


class StatesGroup:
    pass
