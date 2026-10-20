from dataclasses import dataclass, field


class _Obj:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


class InlineKeyboardButton(_Obj):
    def __init__(self, text="", callback_data=None, web_app=None, url=None, **kw):
        super().__init__(text=text, callback_data=callback_data, web_app=web_app, url=url, **kw)


class InlineKeyboardMarkup(_Obj):
    def __init__(self, inline_keyboard=None, **kw):
        super().__init__(inline_keyboard=inline_keyboard or [], **kw)

    def buttons(self):
        return [b for row in self.inline_keyboard for b in row]


class WebAppInfo(_Obj):
    def __init__(self, url="", **kw):
        super().__init__(url=url, **kw)


class MenuButtonWebApp(_Obj):
    pass


class BotCommand(_Obj):
    def __init__(self, command="", description="", **kw):
        super().__init__(command=command, description=description, **kw)


class LabeledPrice(_Obj):
    pass


class FSInputFile(_Obj):
    def __init__(self, path="", **kw):
        super().__init__(path=path, **kw)


class PreCheckoutQuery(_Obj):
    pass


class Message(_Obj):
    """Сообщение в тестах: всё отправленное складывается в .outbox."""

    def __init__(self, chat_id=1, message_id=1, text=None, caption=None, photo=None, document=None, from_user=None, bot=None, outbox=None, **kw):
        super().__init__(chat=_Obj(id=chat_id), message_id=message_id, text=text, caption=caption, photo=photo,
                         document=document, from_user=from_user, bot=bot, outbox=outbox if outbox is not None else [], **kw)

    async def answer(self, text="", reply_markup=None, **kw):
        self.outbox.append({"text": text, "markup": reply_markup})
        return self

    async def answer_photo(self, photo=None, caption="", reply_markup=None, **kw):
        self.outbox.append({"photo": photo, "text": caption, "markup": reply_markup})
        return self

    async def answer_invoice(self, **kw):
        self.outbox.append({"invoice": kw})
        return self


class CallbackQuery(_Obj):
    def __init__(self, data="", from_user=None, message=None, bot=None, **kw):
        super().__init__(data=data, from_user=from_user, message=message, bot=bot, answers=[], **kw)

    async def answer(self, text=None, show_alert=False, **kw):
        self.answers.append({"text": text, "alert": show_alert})
