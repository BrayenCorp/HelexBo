from ..types import InlineKeyboardMarkup


class InlineKeyboardBuilder:
    def __init__(self):
        self._rows = []

    def row(self, *buttons):
        self._rows.append(list(buttons))
        return self

    def button(self, **kw):
        from ..types import InlineKeyboardButton
        self._rows.append([InlineKeyboardButton(**kw)])
        return self

    def as_markup(self):
        return InlineKeyboardMarkup(inline_keyboard=self._rows)
