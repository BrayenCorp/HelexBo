class FSMContext:
    """Память состояния на один чат."""

    def __init__(self):
        self._state = None
        self._data = {}

    async def set_state(self, state=None):
        self._state = str(state) if state is not None else None

    async def get_state(self):
        return self._state

    async def update_data(self, **kw):
        self._data.update(kw)
        return dict(self._data)

    async def get_data(self):
        return dict(self._data)

    async def set_data(self, data):
        self._data = dict(data)

    async def clear(self):
        self._state = None
        self._data = {}
