"""Выполнение заказа: провайдер → файл результата → статус заказа."""
from __future__ import annotations

import logging
from pathlib import Path

from ..ai.base import GenerationRequest, ProviderNotConfigured
from ..ai.registry import ProviderRegistry
from ..db import Database
from ..storage import Storage
from . import orders, params as params_service, templates as tpl_service

log = logging.getLogger(__name__)

NOT_CONNECTED_MESSAGE = "Эта генерация ещё не подключена. Бесплатная попытка и кредиты возвращены."


def process_order(db: Database, storage: Storage, providers: ProviderRegistry, order_id: int) -> dict | None:
    order = orders.claim_for_processing(db, order_id)
    if order is None:  # уже обрабатывается или завершён — повторный запуск безопасен
        return orders.get_order(db, order_id)
    result_path = None
    try:
        with db.read() as conn:
            tpl = conn.execute("SELECT * FROM templates WHERE id = ?", (order["template_id"],)).fetchone()
        model_key = order.get("model") or tpl["model"]
        provider = providers.get(order["kind"], model_key)
        _, style_prompt = tpl_service.resolve_style(tpl["styles"], order.get("style"))
        order_params = orders._loads(order.get("params"))
        prompt = ", ".join(p for p in (
            tpl["prompt"], style_prompt, order.get("prompt") or "", params_service.params_to_prompt(order_params)) if p)
        image = Path(order["input_path"]).read_bytes() if order.get("input_path") else b""
        req = GenerationRequest(
            order_id=order_id, kind=order["kind"], model=model_key, prompt=prompt,
            title=tpl["title"], image=image, params=order_params,
        )
        res = provider.generate(req)
        result_path = storage.save_result(order_id, res.data, res.ext)
        if not orders.complete_order(
            db, order_id, result_path=result_path, mime=res.mime, provider=res.provider,
            cost_usd=res.cost_usd, is_stub=res.is_stub, duration_sec=res.duration_sec,
        ):
            storage.delete(result_path)  # заказ уже закрыт (например, по таймауту)
    except ProviderNotConfigured as e:
        orders.fail_order(db, order_id, str(e), NOT_CONNECTED_MESSAGE, error_type="provider_not_configured", severity="warning")
    except Exception as e:  # любая техническая ошибка → возврат кредитов
        log.exception("Ошибка генерации заказа %s", order_id)
        storage.delete(result_path)
        orders.fail_order(db, order_id, f"{type(e).__name__}: {e}", error_type="provider_error")
    orders.clear_input(db, storage, order_id)  # исходное фото больше не хранится
    return orders.get_order(db, order_id)
