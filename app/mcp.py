"""Сервер MCP (JSON-RPC 2.0 поверх HTTP) для подключения Nolla AI к ChatGPT, Claude, Cursor, Codex и другим клиентам.

Адрес: POST /mcp, заголовок «Authorization: Bearer <личный токен>». Токен создаётся в «Интеграциях» и хранится только хешем.
Инструменты работают от имени владельца токена и используют ту же логику заказов и токенов, что и приложение:
цена берётся из базы, при ошибке токены возвращаются, повтор с тем же request_id ничего не списывает.
Секреты (ключи AI-провайдеров, токен бота) в ответы не попадают и задаются только переменными окружения."""
from __future__ import annotations

import asyncio
import json
import uuid

from . import catalog_data as cd
from .context import AppContext
from .errors import DomainError
from .services import credits, models as models_service, orders

PROTOCOL = "2025-03-26"

_PROMPT = {"type": "string", "description": "Описание на русском или английском"}
_REQ = {"type": "string", "description": "Необязательный идентификатор запроса: повтор с тем же значением не спишет токены второй раз"}
SCHEMAS = {
    "create_image": {"type": "object", "required": ["prompt"], "properties": {
        "prompt": _PROMPT, "model": {"type": "string", "description": "Название модели, например «Nano Banana 2»"},
        "format": {"type": "string", "enum": ["1:1", "3:4", "4:3", "9:16", "16:9", "21:9"]}, "request_id": _REQ}},
    "edit_image": {"type": "object", "required": ["order_id", "prompt"], "properties": {
        "order_id": {"type": "integer", "description": "Номер вашей готовой генерации-изображения"}, "prompt": _PROMPT, "model": {"type": "string"}, "request_id": _REQ}},
    "create_video": {"type": "object", "required": ["prompt"], "properties": {
        "prompt": _PROMPT, "model": {"type": "string"}, "source_order_id": {"type": "integer", "description": "Изображение из вашей истории как первый кадр"}, "request_id": _REQ}},
    "create_audio": {"type": "object", "required": ["text"], "properties": {
        "text": {"type": "string"}, "voice": {"type": "string", "enum": [v for v, _ in cd.VOICES]}, "emotion": {"type": "string", "enum": [e for e, _ in cd.EMOTIONS]},
        "speed": {"type": "number", "minimum": 0.5, "maximum": 2}, "request_id": _REQ}},
    "get_generation_status": {"type": "object", "required": ["order_id"], "properties": {"order_id": {"type": "integer"}}},
    "get_balance": {"type": "object", "properties": {}},
    "get_history": {"type": "object", "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 50}}},
}


def tool_list() -> list[dict]:
    return [{"name": n, "title": t, "description": d, "inputSchema": SCHEMAS[n]} for n, t, d in cd.MCP_TOOLS]


def _model_id(ctx: AppContext, kind: str, name: str | None) -> int | None:
    if not name:
        return None
    for m in models_service.public_list(ctx.db, kind):
        if name.strip().casefold() in (m["name"].casefold(), m["slug"].casefold()):
            return m["id"]
    raise DomainError(f"Модель «{name}» не найдена среди доступных для этого типа")


def _public(ctx: AppContext, user_id: int, order_id: int) -> dict:
    o = orders.get_user_order(ctx.db, user_id, order_id)
    if o is None:
        raise DomainError("Генерация не найдена", code="order_not_found", status=404)
    p = orders.public_order(o)
    status = {"created": "queued", "processing": "processing", "done": "done", "failed": "failed"}[p["status"]]
    out = {"order_id": p["id"], "kind": p["kind"], "status": status, "tokens": p["price_credits"], "demo_result": p["is_stub"], "created_at": p["created_at"]}
    if p["status"] == "done" and p["has_result"]:
        base = ctx.settings.webapp_url
        out["result_url"] = f"{base}/mcp/result/{p['id']}"
        out["result_mime"] = p["result_mime"]
    if p["status"] == "failed":
        out["error"] = p["error"]
    return out


async def _submit(ctx: AppContext, user_id: int, a: dict, **kw) -> dict:
    rid = str(a.get("request_id") or f"mcp-{uuid.uuid4().hex[:16]}")[:100]
    results = await asyncio.to_thread(lambda: orders.submit_generation(ctx.db, ctx.storage, user_id=user_id, request_id=rid, source="mcp",
                                                                       max_bytes=ctx.settings.max_upload_bytes, **kw))
    order, created = results
    if created:
        ctx.runner.schedule(order["id"])
    out = _public(ctx, user_id, order["id"])
    out["balance"] = credits.get_balance(ctx.db, user_id)
    return out


async def call_tool(ctx: AppContext, user_id: int, name: str, a: dict) -> dict:
    if name == "create_image":
        params = {"format": a["format"]} if a.get("format") else None
        return await _submit(ctx, user_id, a, kind="photo", prompt=a.get("prompt", ""), params=params, model_id=_model_id(ctx, "photo", a.get("model")))
    if name == "edit_image":
        return await _submit(ctx, user_id, a, kind="photo", prompt=a.get("prompt", ""), ref_order_id=int(a["order_id"]), model_id=_model_id(ctx, "photo", a.get("model")))
    if name == "create_video":
        ref = int(a["source_order_id"]) if a.get("source_order_id") else None
        return await _submit(ctx, user_id, a, kind="video", prompt=a.get("prompt", ""), ref_order_id=ref, model_id=_model_id(ctx, "video", a.get("model")))
    if name == "create_audio":
        params = {k: a[k] for k in ("voice", "emotion", "speed") if a.get(k) not in (None, "")}
        return await _submit(ctx, user_id, a, kind="audio", prompt=a.get("text", ""), params=params)
    if name == "get_generation_status":
        return _public(ctx, user_id, int(a["order_id"]))
    if name == "get_balance":
        return {"balance": credits.get_balance(ctx.db, user_id), "unit": "токены"}
    if name == "get_history":
        limit = max(1, min(int(a.get("limit") or 10), 50))
        items = orders.list_user_orders(ctx.db, user_id, limit)
        return {"items": [{"order_id": o["id"], "kind": o["kind"], "status": o["status"], "title": o["title"], "prompt": o["prompt"], "tokens": o["price_credits"], "created_at": o["created_at"]} for o in items]}
    raise DomainError(f"Неизвестный инструмент «{name}»", code="unknown_tool")


def _err(id_, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}}


async def handle(ctx: AppContext, user_id: int, msg: dict) -> dict | None:
    """Обрабатывает одно JSON-RPC сообщение. Для уведомлений (без id) возвращает None."""
    id_, method, params = msg.get("id"), msg.get("method"), msg.get("params") or {}
    if method is None or msg.get("jsonrpc") != "2.0":
        return _err(id_, -32600, "Некорректный запрос")
    if id_ is None:
        return None
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": id_, "result": {"protocolVersion": PROTOCOL, "capabilities": {"tools": {}},
                                                       "serverInfo": {"name": "nolla-ai", "version": "1.0"},
                                                       "instructions": "Nolla AI: создание изображений, видео и аудио. Генерации списывают токены владельца токена."}}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": id_, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": id_, "result": {"tools": tool_list()}}
    if method == "tools/call":
        name, args = params.get("name"), params.get("arguments") or {}
        if name not in SCHEMAS:
            return _err(id_, -32602, f"Неизвестный инструмент «{name}»")
        try:
            data = await call_tool(ctx, user_id, name, args)
            return {"jsonrpc": "2.0", "id": id_, "result": {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}], "isError": False}}
        except DomainError as e:
            return {"jsonrpc": "2.0", "id": id_, "result": {"content": [{"type": "text", "text": e.message}], "isError": True}}
        except (KeyError, ValueError, TypeError):
            return {"jsonrpc": "2.0", "id": id_, "result": {"content": [{"type": "text", "text": "Некорректные аргументы инструмента"}], "isError": True}}
    return _err(id_, -32601, "Метод не поддерживается")
