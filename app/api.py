"""Backend API для Mini App и админ-центра Nolla AI (FastAPI).

Авторизация: «Authorization: tma <initData>» — подпись проверяется на сервере. Telegram ID, цена и баланс
никогда не берутся из тела запроса. Админские маршруты проверяют роль на каждом запросе."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, Header, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .context import AppContext
from .errors import DomainError, Forbidden, InvalidInitData
from .security import validate_init_data
from . import catalog_data, mcp as mcp_server
from .services import (
    admin_lists, admin_users, analytics, api_tokens, avatars, catalog, categories, content, credits, events, exports, favorites, frames, landing,
    media, methods, models, orders, payments, prefs, previews, showcase, site_settings, system, templates, users,
)

log = logging.getLogger(__name__)


class PackageIn(BaseModel):
    package_id: str
    method: str = ""


class PayloadIn(BaseModel):
    payload: str


class FavoriteIn(BaseModel):
    kind: str
    ref_id: int
    on: bool = True


class SettingsIn(BaseModel):
    notify_chat: bool


class DemoPayIn(BaseModel):
    package_id: str
    method: str


class PrefsIn(BaseModel):
    ratio: str | None = None
    quality: str | None = None
    autodownload: bool | None = None
    default_model_id: int | None = None
    notify: bool | None = None
    interests: list[str] | None = None
    clear_model: bool = False


class FrameIn(BaseModel):
    index: int
    request_id: str


class MoveIn(BaseModel):
    direction: str


class TokenIn(BaseModel):
    label: str = ""


class ActionIn(BaseModel):
    action: str
    amount: int | None = None
    note: str = ""
    confirm: bool = False


def create_app(ctx: AppContext) -> FastAPI:
    app = FastAPI(title="Nolla AI", docs_url="/api/docs" if ctx.settings.dev_mode else None, redoc_url=None)
    s = ctx.settings
    bot_present = lambda: ctx.bot is not None

    @app.exception_handler(DomainError)
    async def domain_error_handler(_: Request, exc: DomainError):
        return JSONResponse(status_code=exc.status, content={"code": exc.code, "message": exc.message})

    # ---------- авторизация ----------
    async def current_user(authorization: str = Header(default=""), x_dev_user: str = Header(default="")) -> dict:
        if authorization.startswith("tma "):
            tg = validate_init_data(authorization[4:], s.bot_token, max_age=s.init_data_max_age)
        elif s.dev_mode and x_dev_user.isdigit():
            tg = {"id": int(x_dev_user), "username": "dev", "first_name": "Dev"}
        else:
            raise InvalidInitData("Откройте приложение из Telegram")
        users.upsert_user(ctx.db, tg["id"], tg.get("username"), tg.get("first_name"), last_name=tg.get("last_name"),
                          language_code=tg.get("language_code"), photo_url=tg.get("photo_url"), start_param=tg.get("start_param"))
        return tg

    def require(*roles: str):
        async def dep(user: dict = Depends(current_user)) -> dict:
            if not any(r in ctx.access.roles(user["id"]) for r in roles):
                raise Forbidden("Нет доступа")
            return user

        return dep

    owner = require("owner")
    staff = require("owner", "developer")

    def ref_link(tg_id: int) -> str:
        return f"https://t.me/{ctx.bot_username}?start=ref_{tg_id}" if ctx.bot_username else ""

    def period(p: str, start: str | None, end: str | None):
        return analytics.resolve_period(p, start, end)

    # ---------- общее ----------
    @app.get("/api/health")
    async def health():
        return {"ok": True}

    @app.get("/api/me")
    async def me(user: dict = Depends(current_user)):
        prof = users.profile(ctx.db, user["id"])
        prof["roles"] = ctx.access.roles(user["id"])
        prof["modes"] = {"ai": s.ai_mode, "payments": s.payments_mode}
        prof["prefs"] = prefs.get(ctx.db, user["id"])
        prof["favorites"] = favorites.ids(ctx.db, user["id"])
        prof["bot_link"] = f"https://t.me/{ctx.bot_username}" if ctx.bot_username else ""
        prof["ref_link"] = ref_link(user["id"])
        prof["freeform"] = {x["kind"]: {"price": x["price_credits"], "enabled": x["enabled"]} for x in templates.list_system(ctx.db)}
        prof["show_welcome"] = prof["registered"] and not prof["welcomed"]
        with ctx.db.read() as c:
            prof["welcome_bonus"] = c.execute("SELECT COALESCE(SUM(delta),0) FROM credit_ledger WHERE user_id = ? AND reason = 'welcome_bonus'", (user["id"],)).fetchone()[0]
            prof["max_variants"] = site_settings.get_int(c, "max_variants", 4)
        return prof

    @app.post("/api/register")
    async def register(user: dict = Depends(current_user)):
        """Вход через Telegram: создаёт аккаунт, при включённом бонусе начисляет стартовые токены."""
        _, newly = users.register(ctx.db, user["id"])
        return {"registered": True, "new": newly, "balance": credits.get_balance(ctx.db, user["id"])}

    @app.post("/api/welcomed")
    async def welcomed(user: dict = Depends(current_user)):
        users.mark_welcomed(ctx.db, user["id"])
        return {"ok": True}

    @app.post("/api/event/open")
    async def event_open(user: dict = Depends(current_user)):
        events.log(ctx.db, "miniapp_opened", user["id"])
        return {"ok": True}

    @app.get("/api/profile")
    async def profile(user: dict = Depends(current_user)):
        prof = users.profile(ctx.db, user["id"])
        fav = favorites.ids(ctx.db, user["id"])
        done = orders.count_done_by_kind(ctx.db, user["id"])
        return {
            "id": user["id"], "first_name": prof["first_name"], "username": prof["username"], "balance": prof["balance"], "is_pro": prof["is_pro"],
            "generations": done["photo"] + done["video"] + done["audio"], "images": done["photo"], "videos": done["video"], "audios": done["audio"], "favorites_count": len(fav["orders"]),
            "support_url": site_settings.get_all(ctx.db).get("support_url", ""), "roles": ctx.access.roles(user["id"]), "ref_link": ref_link(user["id"]),
            "created_at": prof.get("created_at"),
        }

    @app.put("/api/me/settings")
    async def my_settings(body: SettingsIn, user: dict = Depends(current_user)):
        users.set_notify_chat(ctx.db, user["id"], body.notify_chat)
        return {"notify_chat": body.notify_chat}

    @app.delete("/api/me/media")
    async def delete_my_media(user: dict = Depends(current_user)):
        n = await asyncio.to_thread(orders.delete_user_media, ctx.db, ctx.storage, user["id"])
        n += await asyncio.to_thread(avatars.delete_all, ctx.db, ctx.storage, user["id"])
        return {"deleted_files": n}

    @app.get("/api/me/prefs")
    async def get_prefs(user: dict = Depends(current_user)):
        return prefs.get(ctx.db, user["id"])

    @app.put("/api/me/prefs")
    async def put_prefs(body: PrefsIn, user: dict = Depends(current_user)):
        data = body.model_dump(exclude_none=True)
        if data.pop("clear_model", False):
            data["default_model_id"] = None
        return prefs.update(ctx.db, user["id"], data)

    @app.get("/api/categories")
    async def list_categories(_: dict = Depends(current_user)):
        return categories.list_public(ctx.db)

    @app.get("/api/categories/{category_id}")
    async def get_category(category_id: str, _: dict = Depends(current_user)):
        return categories.get_public(ctx.db, category_id)

    @app.get("/api/home")
    async def home(_: dict = Depends(current_user)):
        return landing.build(ctx.db, s, bot_present())

    @app.get("/api/models")
    async def list_models(kind: str | None = None, _: dict = Depends(current_user)):
        return models.public_list(ctx.db, kind)

    @app.get("/api/templates")
    async def list_templates(kind: str | None = None, category: str | None = None, q: str | None = None,
                             collection: str | None = None, _: dict = Depends(current_user)):
        return templates.list_published(ctx.db, kind, category, q, collection)

    @app.get("/api/templates/{template_id}")
    async def get_template(template_id: int, _: dict = Depends(current_user)):
        return templates.get_published(ctx.db, template_id)

    # ---------- платформа: каталог, поиск, главная ----------
    @app.get("/api/platform/meta")
    async def platform_meta(_: dict = Depends(current_user)):
        return catalog.meta(ctx.db)

    @app.get("/api/platform/home")
    async def platform_home(user: dict = Depends(current_user)):
        ideas = catalog.list_items(ctx.db, "idea", on_home=True, limit=10)
        popular = list(ideas)
        if len(popular) < 6:  # пока витрина не заполнена — показываем популярное из каталога
            for sec in ("effect", "trend", "photoshoot", "marketing"):
                popular += catalog.list_items(ctx.db, sec, popular=True, limit=3)
        recent = [orders.public_order(o) for o in orders.list_user_orders(ctx.db, user["id"], 8)]
        return {"popular": popular[:10], "ideas": ideas, "trends": catalog.list_items(ctx.db, "trend", limit=8),
                "photoshoots": catalog.list_items(ctx.db, "photoshoot", limit=8), "recent": recent, "demo": s.ai_mode == "mock"}

    @app.get("/api/ideas")
    async def ideas(tag: str | None = None, q: str | None = None, _: dict = Depends(current_user)):
        """Витрина «Идеи»: карточки, которые владелец добавил в админке.
        Пока витрина пустая, показываем тренды и фотосессии, чтобы раздел не был пустым."""
        items = catalog.list_items(ctx.db, "idea", tag, q, on_ideas=True)
        if items or (tag and tag != "all"):
            return items
        return catalog.list_items(ctx.db, "trend", q=q, limit=12) + catalog.list_items(ctx.db, "photoshoot", q=q, limit=12)

    @app.get("/api/catalog/{section}")
    async def catalog_list(section: str, tag: str | None = None, q: str | None = None, popular: bool = False, _: dict = Depends(current_user)):
        return catalog.list_items(ctx.db, section, tag, q, popular)

    @app.get("/api/catalog/item/{item_id}")
    async def catalog_item(item_id: int, _: dict = Depends(current_user)):
        return catalog.get_item(ctx.db, item_id)

    @app.get("/api/catalog/slug/{slug}")
    async def catalog_slug(slug: str, _: dict = Depends(current_user)):
        return catalog.get_by_slug(ctx.db, slug)

    @app.get("/api/previews")
    async def preview_photos(_: dict = Depends(current_user)):
        """Ваши фото для обложек карточек (папка data/media/previews)."""
        return previews.list_public(ctx.storage)

    @app.get("/api/search")
    async def search(q: str = "", user: dict = Depends(current_user)):
        return catalog.search(ctx.db, user["id"], q)

    @app.get("/api/quote")
    async def quote(kind: str | None = None, template_id: int | None = None, model_id: int | None = None, count: int = 1, user: dict = Depends(current_user)):
        q = orders.quote(ctx.db, user["id"], template_id=template_id, kind=kind, model_id=model_id)
        with ctx.db.read() as c:
            count = max(1, min(count, site_settings.get_int(c, "max_variants", 4)))
        total = (0 if q["free"] else q["base"]) + q["base"] * (count - 1)
        bal = credits.get_balance(ctx.db, user["id"])
        return {**q, "count": count, "total": total, "balance": bal, "enough": bal >= total}

    # ---------- аватары ----------
    @app.get("/api/avatars")
    async def my_avatars(user: dict = Depends(current_user)):
        return avatars.list_for_user(ctx.db, user["id"])

    @app.post("/api/avatars")
    async def create_avatar(name: str = Form(default=""), consent: bool = Form(default=False), photos: list[UploadFile] = File(default=[]),
                            user: dict = Depends(current_user)):
        files = [await f.read(s.max_upload_bytes + 1) for f in photos]
        row = await asyncio.to_thread(avatars.create, ctx.db, ctx.storage, user["id"], name, files, consent, s.max_upload_bytes)
        ctx.runner.schedule_avatar(row["id"])
        return avatars.public(row)

    @app.get("/api/avatars/{avatar_id}")
    async def one_avatar(avatar_id: int, user: dict = Depends(current_user)):
        return avatars.public(avatars.get_owned(ctx.db, user["id"], avatar_id))

    @app.get("/api/avatars/{avatar_id}/cover")
    async def avatar_cover(avatar_id: int, user: dict = Depends(current_user)):
        return FileResponse(avatars.cover_file(ctx.db, user["id"], avatar_id), media_type="image/jpeg")

    @app.delete("/api/avatars/{avatar_id}")
    async def delete_avatar(avatar_id: int, user: dict = Depends(current_user)):
        await asyncio.to_thread(avatars.delete, ctx.db, ctx.storage, user["id"], avatar_id)
        return {"deleted": True}

    # ---------- интеграции (MCP) ----------
    @app.get("/api/integrations")
    async def integrations(user: dict = Depends(current_user)):
        return {"endpoint": f"{s.webapp_url}/mcp" if s.webapp_url else "/mcp", "clients": [{"name": n, "how": h} for n, h in catalog_data.MCP_CLIENTS],
                "tools": [{"name": n, "title": t, "description": d} for n, t, d in catalog_data.MCP_TOOLS], "tokens": api_tokens.list_for_user(ctx.db, user["id"])}

    @app.post("/api/integrations/tokens")
    async def create_token(body: TokenIn, user: dict = Depends(current_user)):
        return api_tokens.create(ctx.db, user["id"], body.label)

    @app.delete("/api/integrations/tokens/{token_id}")
    async def revoke_token(token_id: int, user: dict = Depends(current_user)):
        api_tokens.revoke(ctx.db, user["id"], token_id)
        return {"revoked": True}

    async def mcp_user(authorization: str = Header(default="")) -> int:
        uid = api_tokens.authenticate(ctx.db, authorization[7:].strip()) if authorization.lower().startswith("bearer ") else None
        if uid is None:
            raise InvalidInitData("Нужен личный токен: Authorization: Bearer <токен>")
        return uid

    @app.post("/mcp")
    async def mcp_endpoint(request: Request, uid: int = Depends(mcp_user)):
        try:
            payload = await request.json()
        except ValueError:
            return JSONResponse(status_code=400, content={"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Некорректный JSON"}})
        if isinstance(payload, list):
            out = [r for r in [await mcp_server.handle(ctx, uid, m) for m in payload if isinstance(m, dict)] if r is not None]
            return JSONResponse(out) if out else Response(status_code=202)
        res = await mcp_server.handle(ctx, uid, payload if isinstance(payload, dict) else {})
        return JSONResponse(res) if res is not None else Response(status_code=202)

    @app.get("/mcp/result/{order_id}")
    async def mcp_result(order_id: int, uid: int = Depends(mcp_user)):
        o = orders.get_user_order(ctx.db, uid, order_id)
        if o is None or o["status"] != "done" or not o["result_path"] or not Path(o["result_path"]).exists():
            raise DomainError("Результат не найден", code="result_not_found", status=404)
        return FileResponse(o["result_path"], media_type=o["result_mime"] or "application/octet-stream")

    # ---------- избранное ----------
    @app.get("/api/favorites")
    async def my_favorites(user: dict = Depends(current_user)):
        return favorites.list_all(ctx.db, user["id"])

    @app.post("/api/favorites")
    async def set_favorite(body: FavoriteIn, user: dict = Depends(current_user)):
        return favorites.set_favorite(ctx.db, user["id"], body.kind, body.ref_id, body.on)

    # ---------- заказы ----------
    @app.post("/api/orders")
    async def create_order(
        request_id: str = Form(...), template_id: int | None = Form(default=None), kind: str = Form(default=""),
        prompt: str = Form(default=""), params: str = Form(default=""), style: str = Form(default=""),
        model_id: int | None = Form(default=None), count: int = Form(default=1), avatar_id: int | None = Form(default=None),
        ref_order_id: int | None = Form(default=None),
        photo: UploadFile | None = File(default=None), photo2: UploadFile | None = File(default=None), user: dict = Depends(current_user),
    ):
        """Два режима: по шаблону (template_id) и свободный (kind + prompt [+ model_id]). Фото необязательно."""
        data = await photo.read(s.max_upload_bytes + 1) if photo is not None else None
        data2 = await photo2.read(s.max_upload_bytes + 1) if photo2 is not None else None
        results = await asyncio.to_thread(
            lambda: orders.submit_variants(
                ctx.db, ctx.storage, count=count, user_id=user["id"], request_id=request_id, source="app", template_id=template_id,
                kind=kind or None, image_bytes=data, prompt=prompt, params=params or None, max_bytes=s.max_upload_bytes,
                style=style or None, model_id=model_id, image2_bytes=data2, avatar_id=avatar_id, ref_order_id=ref_order_id))
        for order, created in results:
            if created:
                ctx.runner.schedule(order["id"])
        pub = [orders.public_order(orders.get_user_order(ctx.db, user["id"], o["id"])) for o, _ in results]
        return {"order": pub[0], "orders": pub, "created": any(c for _, c in results), "balance": credits.get_balance(ctx.db, user["id"]),
                "free": orders.free_status(ctx.db, user["id"])}

    @app.get("/api/orders")
    async def my_orders(user: dict = Depends(current_user)):
        return [orders.public_order(o) for o in orders.list_user_orders(ctx.db, user["id"], 200)]

    @app.get("/api/orders/{order_id}")
    async def my_order(order_id: int, user: dict = Depends(current_user)):
        o = orders.get_user_order(ctx.db, user["id"], order_id)
        if o is None:
            raise DomainError("Заказ не найден", code="order_not_found", status=404)
        return orders.public_order(o)

    @app.get("/api/orders/{order_id}/result")
    async def order_result(order_id: int, user: dict = Depends(current_user)):
        o = orders.get_user_order(ctx.db, user["id"], order_id)
        if o is None or o["status"] != "done" or not o["result_path"] or not Path(o["result_path"]).exists():
            raise DomainError("Результат не найден", code="result_not_found", status=404)
        return FileResponse(o["result_path"], media_type=o["result_mime"] or "application/octet-stream")

    @app.get("/api/orders/{order_id}/frames/{index}")
    async def order_frame(order_id: int, index: int, user: dict = Depends(current_user)):
        o = orders.get_user_order(ctx.db, user["id"], order_id)
        path = orders.frame_path(o, index) if o else None
        if not path or not Path(path).exists():
            raise DomainError("Кадр не найден", code="result_not_found", status=404)
        return FileResponse(path, media_type="image/jpeg")

    @app.post("/api/orders/{order_id}/regen-frame")
    async def regen_frame(order_id: int, body: FrameIn, user: dict = Depends(current_user)):
        order = await asyncio.to_thread(frames.regen_frame, ctx.db, ctx.storage, ctx.providers, user_id=user["id"], order_id=order_id,
                                        index=body.index, request_id=body.request_id)
        return {"order": order, "balance": credits.get_balance(ctx.db, user["id"]), "price": frames.regen_price(ctx.db)}

    @app.delete("/api/orders/{order_id}")
    async def delete_order(order_id: int, user: dict = Depends(current_user)):
        await asyncio.to_thread(orders.delete_order, ctx.db, ctx.storage, user["id"], order_id)
        return {"deleted": True}

    @app.post("/api/orders/{order_id}/send-to-chat")
    async def send_to_chat(order_id: int, user: dict = Depends(current_user)):
        o = orders.get_user_order(ctx.db, user["id"], order_id)
        if o is None or o["status"] != "done" or not o["result_path"]:
            raise DomainError("Результат не найден", code="result_not_found", status=404)
        if ctx.runner.notifier is None:
            raise DomainError("Бот не запущен — отправка в чат недоступна", code="chat_unavailable", status=503)
        try:
            await ctx.runner.notifier.notify_order(o, with_menu=False)
        except Exception:
            log.warning("Не удалось отправить результат %s в чат", order_id, exc_info=True)
            raise DomainError("Не удалось отправить в чат. Откройте бота и нажмите /start.", code="chat_failed", status=502)
        return {"sent": True}

    # ---------- токены и оплата ----------
    @app.get("/api/packages")
    async def packages(_: dict = Depends(current_user)):
        return [{"id": p["id"], "title": p["title"], "credits": p["credits"], "bonus": p["bonus"], "price_stars": p["price_stars"],
                 "old_price_stars": p["old_price_stars"], "price_rub": p["price_rub"], "badge": p["badge"]} for p in payments.list_packages(ctx.db)]

    @app.get("/api/payment-methods")
    async def payment_methods(_: dict = Depends(current_user)):
        return methods.for_users(ctx.db, s, bot_present())

    @app.get("/api/tokens")
    async def tokens(user: dict = Depends(current_user)):
        return credits.summary(ctx.db, user["id"])

    @app.get("/api/ledger")
    async def ledger(user: dict = Depends(current_user)):
        return credits.get_ledger(ctx.db, user["id"])

    @app.get("/api/payments/history")
    async def payments_history(user: dict = Depends(current_user)):
        return payments.list_user_payments(ctx.db, user["id"])

    @app.post("/api/payments/start")
    async def start_payment(body: PackageIn, user: dict = Depends(current_user)):
        avail = methods.for_users(ctx.db, s, bot_present())["available"]
        method = body.method or (avail[0]["code"] if avail else "")
        if not methods.is_available(ctx.db, s, bot_present(), method):
            raise DomainError("Этот способ оплаты сейчас недоступен", code="payments_disabled", status=503)
        pay = payments.create_payment(ctx.db, user["id"], body.package_id, method)
        link = None
        if method == "stars":
            from aiogram.types import LabeledPrice

            pkg = next(p for p in payments.list_packages(ctx.db) if p["id"] == pay["package_id"])
            link = await ctx.bot.create_invoice_link(
                title=f"{pkg['title']}: {pkg['credits'] + pkg['bonus']} токенов", description="Токены для создания фото и видео в Nolla AI",
                payload=pay["payload"], currency="XTR", provider_token="", prices=[LabeledPrice(label=pkg["title"], amount=pay["amount_stars"])])
        return {"payment_id": pay["id"], "payload": pay["payload"], "mode": method, "invoice_link": link}

    @app.post("/api/payments/demo")
    async def demo_pay(body: DemoPayIn, user: dict = Depends(current_user)):
        """ДЕМО-оплата без реальных денег (только при PAYMENTS_MODE=test)."""
        if s.payments_mode != "test":
            raise Forbidden("Демо-оплата отключена")
        pay, credited = payments.demo_payment(ctx.db, user["id"], body.package_id, body.method)
        return {"status": pay["status"], "credited": credited, "tokens": pay["credits"] + pay["bonus"], "balance": credits.get_balance(ctx.db, user["id"])}

    @app.post("/api/payments/test-confirm")
    async def test_confirm(body: PayloadIn, user: dict = Depends(current_user)):
        if s.payments_mode != "test":
            raise Forbidden("Тестовая оплата отключена")
        pay, credited = payments.confirm_payment(ctx.db, body.payload, provider="test", user_id=user["id"])
        return {"status": pay["status"], "credited": credited, "balance": credits.get_balance(ctx.db, user["id"])}

    # =====================  АДМИН-ЦЕНТР  =====================
    A = "/api/admin"

    # --- аналитика ---
    @app.get(f"{A}/analytics/overview")
    async def a_overview(period_: str = Query("30d", alias="period"), start: str | None = None, end: str | None = None, _: dict = Depends(owner)):
        a, b = period(period_, start, end)
        return analytics.overview(ctx.db, a, b, s.star_usd_rate)

    @app.get(f"{A}/analytics/series")
    async def a_series(period_: str = Query("30d", alias="period"), start: str | None = None, end: str | None = None, _: dict = Depends(owner)):
        a, b = period(period_, start, end)
        return analytics.series(ctx.db, a, b)

    @app.get(f"{A}/analytics/retention")
    async def a_retention(days: int = 30, _: dict = Depends(owner)):
        return analytics.retention(ctx.db, max(7, min(days, 90)))

    @app.get(f"{A}/analytics/funnel")
    async def a_funnel(period_: str = Query("30d", alias="period"), start: str | None = None, end: str | None = None, _: dict = Depends(owner)):
        a, b = period(period_, start, end)
        return analytics.funnel(ctx.db, a, b)

    @app.get(f"{A}/analytics/popularity")
    async def a_popularity(period_: str = Query("30d", alias="period"), start: str | None = None, end: str | None = None, _: dict = Depends(owner)):
        a, b = period(period_, start, end)
        return analytics.popularity(ctx.db, a, b)

    @app.get(f"{A}/analytics/bot")
    async def a_bot(period_: str = Query("30d", alias="period"), start: str | None = None, end: str | None = None, _: dict = Depends(owner)):
        a, b = period(period_, start, end)
        return analytics.bot_stats(ctx.db, a, b)

    @app.get(f"{A}/analytics/revenue")
    async def a_revenue(period_: str = Query("30d", alias="period"), start: str | None = None, end: str | None = None, _: dict = Depends(owner)):
        a, b = period(period_, start, end)
        return analytics.revenue_report(ctx.db, a, b, s.star_usd_rate)

    @app.get(f"{A}/analytics/tokens")
    async def a_tokens(period_: str = Query("30d", alias="period"), start: str | None = None, end: str | None = None, _: dict = Depends(owner)):
        a, b = period(period_, start, end)
        return {**analytics.tokens_flow(ctx.db, a, b), "welcome_bonus": site_settings.get_all(ctx.db)["welcome_bonus"]}

    @app.get(f"{A}/analytics/providers")
    async def a_providers(period_: str = Query("30d", alias="period"), start: str | None = None, end: str | None = None, _: dict = Depends(staff)):
        a, b = period(period_, start, end)
        stats = {p["model"]: p for p in analytics.providers(ctx.db, a, b)}
        known = ctx.providers.describe()
        return {"items": stats and list(stats.values()), "connected": known}

    @app.get(f"{A}/activity")
    async def a_activity(limit: int = 50, kinds: str = "", _: dict = Depends(owner)):
        return admin_lists.activity_feed(ctx.db, limit=limit, kinds=set(k for k in kinds.split(",") if k) or None)

    # --- пользователи ---
    @app.get(f"{A}/users")
    async def a_users(q: str = "", flt: str = "all", page: int = 1, size: int = 25, sort: str = "", desc: bool = True, _: dict = Depends(owner)):
        return admin_users.users_list(ctx.db, q=q, flt=flt, page=page, size=size, sort=sort, desc=desc)

    @app.get(f"{A}/users/{{tg_id}}")
    async def a_user(tg_id: int, _: dict = Depends(owner)):
        return admin_users.user_profile(ctx.db, tg_id, s.star_usd_rate)

    @app.post(f"{A}/users/{{tg_id}}/action")
    async def a_user_action(tg_id: int, body: ActionIn, admin: dict = Depends(owner)):
        return admin_users.act(ctx.db, admin, tg_id, body.action, amount=body.amount, note=body.note, confirm=body.confirm)

    @app.get(f"{A}/audit")
    async def a_audit(page: int = 1, _: dict = Depends(owner)):
        return admin_users.audit_list(ctx.db, page)

    # --- генерации, платежи, ошибки, рефералы, маркетинг, система ---
    @app.get(f"{A}/generations")
    async def a_generations(kind: str = "", status: str = "", provider: str = "", category: str = "", start: str = "", end: str = "",
                            q: str = "", page: int = 1, size: int = 25, _: dict = Depends(staff)):
        return admin_lists.generations_list(ctx.db, kind=kind, status=status, provider=provider, category=category, start=start, end=end, q=q, page=page, size=size)

    @app.get(f"{A}/payments")
    async def a_payments(status: str = "", method: str = "", q: str = "", page: int = 1, size: int = 25, _: dict = Depends(owner)):
        return admin_lists.payments_list(ctx.db, status=status, method=method, q=q, page=page, size=size)

    @app.get(f"{A}/errors")
    async def a_errors(severity: str = "", provider: str = "", page: int = 1, size: int = 25, _: dict = Depends(staff)):
        return admin_lists.errors_report(ctx.db, severity=severity, provider=provider, page=page, size=size)

    @app.get(f"{A}/referrals")
    async def a_referrals(_: dict = Depends(owner)):
        return admin_lists.referrals(ctx.db, ctx.bot_username)

    @app.get(f"{A}/marketing")
    async def a_marketing(_: dict = Depends(owner)):
        return admin_lists.marketing(ctx.db, ctx.bot_username)

    @app.get(f"{A}/system")
    async def a_system(_: dict = Depends(staff)):
        return await system.health(ctx)

    @app.get(f"{A}/config")
    async def a_config(_: dict = Depends(owner)):
        return {"owners": sorted(s.owner_ids), "developers": sorted(s.developer_ids), "star_usd_rate": s.star_usd_rate, "ai_mode": s.ai_mode,
                "payments_mode": s.payments_mode, "bot_username": ctx.bot_username, "webapp_url": s.webapp_url, "event_dictionary": events.LABELS, "derived_events": events.DERIVED}

    # --- экспорт ---
    @app.get(f"{A}/export/{{kind}}")
    async def a_export(kind: str, _: dict = Depends(owner)):
        name, data = await asyncio.to_thread(exports.build, ctx.db, kind, s.star_usd_rate, ctx.bot_username)
        return Response(content=data, media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{name}"'})

    @app.post(f"{A}/export/{{kind}}/send")
    async def a_export_send(kind: str, admin: dict = Depends(owner)):
        """В Telegram файлы из Mini App скачиваются неудобно — присылаем CSV в личный чат с ботом."""
        if ctx.bot is None:
            raise DomainError("Бот не запущен", code="chat_unavailable", status=503)
        from aiogram.types import BufferedInputFile

        name, data = await asyncio.to_thread(exports.build, ctx.db, kind, s.star_usd_rate, ctx.bot_username)
        try:
            await ctx.bot.send_document(admin["id"], BufferedInputFile(data, filename=name), caption=f"Экспорт: {exports.KINDS[kind]}")
        except Exception:
            raise DomainError("Не удалось отправить файл. Откройте бота и нажмите /start.", code="chat_failed", status=502)
        return {"sent": True}

    # --- шаблоны ---
    @app.get(f"{A}/templates")
    async def a_templates(_: dict = Depends(owner)):
        items = templates.admin_list(ctx.db)
        with ctx.db.read() as c:
            uses = {r[0]: r[1] for r in c.execute("SELECT template_id, COUNT(*) FROM orders GROUP BY template_id")}
        for t in items:
            t.pop("prompt", None)
            t["styles_count"] = len(templates.parse_styles(t.pop("styles", "[]")))
            t["uses"] = uses.get(t["id"], 0)
        return {"items": items, "categories": [{"id": c["id"], "title": c["title"]} for c in categories.admin_list(ctx.db)], "models": list(templates.KNOWN_MODELS)}

    @app.get(f"{A}/templates/{{template_id}}")
    async def a_template_get(template_id: int, _: dict = Depends(owner)):
        return templates.admin_get(ctx.db, template_id)

    @app.post(f"{A}/templates")
    async def a_template_create(body: dict, _: dict = Depends(owner)):
        return templates.admin_get(ctx.db, templates.create(ctx.db, body)["id"])

    @app.put(f"{A}/templates/{{template_id}}")
    async def a_template_update(template_id: int, body: dict, _: dict = Depends(owner)):
        templates.update(ctx.db, template_id, body)
        return templates.admin_get(ctx.db, template_id)

    @app.delete(f"{A}/templates/{{template_id}}")
    async def a_template_delete(template_id: int, _: dict = Depends(owner)):
        return templates.delete(ctx.db, template_id)

    # --- категории ---
    @app.get(f"{A}/categories")
    async def a_categories(_: dict = Depends(owner)):
        return categories.admin_list(ctx.db)

    @app.post(f"{A}/categories")
    async def a_category_create(body: dict, _: dict = Depends(owner)):
        return categories.create(ctx.db, body)

    @app.put(f"{A}/categories/{{category_id}}")
    async def a_category_update(category_id: str, body: dict, _: dict = Depends(owner)):
        return categories.update(ctx.db, category_id, body)

    @app.delete(f"{A}/categories/{{category_id}}")
    async def a_category_delete(category_id: str, _: dict = Depends(owner)):
        categories.delete(ctx.db, category_id)
        return {"deleted": True}

    # --- пакеты токенов, способы оплаты ---
    @app.get(f"{A}/packages")
    async def a_packages(_: dict = Depends(owner)):
        return payments.admin_list_packages(ctx.db)

    @app.post(f"{A}/packages")
    async def a_package_create(body: dict, _: dict = Depends(owner)):
        return payments.create_package(ctx.db, body)

    @app.put(f"{A}/packages/{{package_id}}")
    async def a_package_update(package_id: str, body: dict, _: dict = Depends(owner)):
        return payments.update_package(ctx.db, package_id, body)

    @app.delete(f"{A}/packages/{{package_id}}")
    async def a_package_delete(package_id: str, _: dict = Depends(owner)):
        return payments.delete_package(ctx.db, package_id)

    @app.get(f"{A}/payment-methods")
    async def a_methods(_: dict = Depends(owner)):
        return methods.admin_list(ctx.db, s, bot_present())

    @app.put(f"{A}/payment-methods/{{code}}")
    async def a_method_update(code: str, body: dict, _: dict = Depends(owner)):
        return methods.update(ctx.db, code, body)

    # --- AI-модели ---
    @app.get(f"{A}/models")
    async def a_models(_: dict = Depends(staff)):
        return {"items": models.admin_list(ctx.db), "providers": ctx.providers.describe(), "provider_keys": list(templates.KNOWN_MODELS)}

    @app.post(f"{A}/models")
    async def a_model_create(body: dict, _: dict = Depends(owner)):
        return models.create(ctx.db, body)

    @app.put(f"{A}/models/{{model_id}}")
    async def a_model_update(model_id: int, body: dict, _: dict = Depends(owner)):
        return models.update(ctx.db, model_id, body)

    @app.delete(f"{A}/models/{{model_id}}")
    async def a_model_delete(model_id: int, _: dict = Depends(owner)):
        return models.delete(ctx.db, model_id)

    # --- контент и FAQ ---
    @app.get(f"{A}/content")
    async def a_content(_: dict = Depends(owner)):
        return content.get_all(ctx.db)

    @app.put(f"{A}/content/{{name}}")
    async def a_content_update(name: str, body: dict, _: dict = Depends(owner)):
        return content.update(ctx.db, name, body.get("value"))

    @app.get(f"{A}/faq")
    async def a_faq(_: dict = Depends(owner)):
        return content.faq_admin(ctx.db)

    @app.post(f"{A}/faq")
    async def a_faq_create(body: dict, _: dict = Depends(owner)):
        return content.faq_save(ctx.db, body)

    @app.put(f"{A}/faq/{{faq_id}}")
    async def a_faq_update(faq_id: int, body: dict, _: dict = Depends(owner)):
        return content.faq_save(ctx.db, body, faq_id)

    @app.delete(f"{A}/faq/{{faq_id}}")
    async def a_faq_delete(faq_id: int, _: dict = Depends(owner)):
        content.faq_delete(ctx.db, faq_id)
        return {"deleted": True}

    # --- витрина, настройки, свободная генерация, медиа ---
    @app.get(f"{A}/showcase")
    async def a_showcase(_: dict = Depends(owner)):
        return showcase.admin_list(ctx.db)

    @app.post(f"{A}/showcase")
    async def a_showcase_create(body: dict, _: dict = Depends(owner)):
        return showcase.create(ctx.db, body)

    @app.put(f"{A}/showcase/{{item_id}}")
    async def a_showcase_update(item_id: int, body: dict, _: dict = Depends(owner)):
        return showcase.update(ctx.db, item_id, body)

    @app.delete(f"{A}/showcase/{{item_id}}")
    async def a_showcase_delete(item_id: int, _: dict = Depends(owner)):
        showcase.delete(ctx.db, item_id)
        return {"deleted": True}

    @app.get(f"{A}/settings")
    async def a_settings(_: dict = Depends(owner)):
        return site_settings.get_all(ctx.db)

    @app.put(f"{A}/settings")
    async def a_settings_update(body: dict, _: dict = Depends(owner)):
        return site_settings.update(ctx.db, body)

    @app.get(f"{A}/freeform")
    async def a_freeform(_: dict = Depends(owner)):
        return {"items": templates.list_system(ctx.db), "models": list(templates.KNOWN_MODELS)}

    @app.put(f"{A}/freeform/{{kind}}")
    async def a_freeform_update(kind: str, body: dict, _: dict = Depends(owner)):
        return templates.update_system(ctx.db, kind, body)

    @app.post(f"{A}/templates/{{template_id}}/duplicate")
    async def a_template_duplicate(template_id: int, _: dict = Depends(owner)):
        return templates.duplicate(ctx.db, template_id)

    @app.post(f"{A}/templates/{{template_id}}/move")
    async def a_template_move(template_id: int, body: MoveIn, _: dict = Depends(owner)):
        return templates.move(ctx.db, template_id, body.direction)

    @app.get(f"{A}/dashboard")
    async def a_dashboard(_: dict = Depends(staff)):
        """Сводка главной админки: всё считается из базы, без заглушек."""
        return analytics.dashboard(ctx.db)

    @app.get(f"{A}/bot-stats")
    async def a_bot_stats(period_: str = Query("30d", alias="period"), start: str | None = None, end: str | None = None, _: dict = Depends(owner)):
        a, b = period(period_, start, end)
        return analytics.bot_stats(ctx.db, a, b)

    @app.get(f"{A}/previews")
    async def a_previews(_: dict = Depends(owner)):
        return previews.list_admin(ctx.storage)

    @app.post(f"{A}/previews")
    async def a_preview_add(file: UploadFile = File(...), _: dict = Depends(owner)):
        data = await file.read(s.max_upload_bytes + 1)
        return await asyncio.to_thread(previews.save, ctx.storage, data, s.max_upload_bytes)

    @app.delete(f"{A}/previews/{{name}}")
    async def a_preview_delete(name: str, _: dict = Depends(owner)):
        previews.delete(ctx.storage, name)
        return {"deleted": True}

    @app.post(f"{A}/media")
    async def a_media(file: UploadFile = File(...), _: dict = Depends(owner)):
        data = await file.read(s.max_video_bytes + 1)
        return await asyncio.to_thread(media.save_media, ctx.storage, data, max_image=20 * 1024 * 1024, max_video=s.max_video_bytes)

    # ---------- собранный frontend ----------
    app.mount("/media", StaticFiles(directory=ctx.storage.media), name="media")
    dist = Path(s.webapp_dist)
    if dist.is_dir():
        app.mount("/", StaticFiles(directory=dist, html=True), name="webapp")
    return app
