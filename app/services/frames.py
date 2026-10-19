"""Кадры раскадровки и ракурсы: просмотр, скачивание и перегенерация одного кадра."""
from __future__ import annotations

import io
import json
from pathlib import Path

from PIL import Image

from ..ai.base import ProviderNotConfigured
from ..ai.registry import ProviderRegistry
from ..db import Database
from ..errors import DomainError, DuplicateOperation
from ..storage import Storage
from . import credits, orders, site_settings

COLS = {"storyboard": (3, (512, 288)), "angles": (3, (384, 480))}


def regen_price(db: Database) -> int:
    with db.read() as conn:
        return site_settings.get_int(conn, "frame_regen_price", 4)


def regen_frame(db: Database, storage: Storage, providers: ProviderRegistry, *, user_id: int, order_id: int, index: int, request_id: str) -> dict:
    """Перегенерировать один кадр. Стоит фиксированное число токенов; при ошибке токены возвращаются; повтор с тем же request_id ничего не списывает."""
    from ..ai.mock import make_sheet

    if not request_id or len(request_id) > 64:
        raise DomainError("Некорректный идентификатор запроса", code="bad_request")
    o = orders.get_user_order(db, user_id, order_id)
    if o is None:
        raise DomainError("Работа не найдена", code="order_not_found", status=404)
    frames = orders._frames(o)
    if o["status"] != "done" or not frames or not 0 <= index < len(frames) or o.get("tool") not in COLS:
        raise DomainError("У этой работы нет кадров для перегенерации", code="no_frames")
    price = regen_price(db)
    reason = f"frame_regen:{request_id}"
    try:
        with db.tx() as conn:
            credits.apply(conn, user_id, -price, reason, order_id=order_id)
    except DuplicateOperation:
        return orders.public_order(orders.get_user_order(db, user_id, order_id))
    old = frames[index]
    try:
        provider = providers.get("photo", "image-default")
        redo = getattr(provider, "redo_frame", None)
        if redo is None:
            raise ProviderNotConfigured("Перегенерация кадра ещё не подключена к провайдеру")
        data = redo(Path(old["path"]).read_bytes(), old["label"], hash((order_id, index, request_id)) & 0x7FFFFFFF)
        new_path = storage.save_result(order_id, data, "jpg")
        frames[index] = {"label": old["label"], "path": new_path}
        cols, cell = COLS[o["tool"]]
        sheet = make_sheet([(f["label"], Path(f["path"]).read_bytes()) for f in frames], cols, cell)
        buf = io.BytesIO()
        from ..ai.mock import _banner
        _banner(sheet).save(buf, "JPEG", quality=88)
        sheet_path = storage.save_result(order_id, buf.getvalue(), "jpg")
    except Exception as e:
        with db.tx() as conn:
            credits.apply(conn, user_id, price, f"frame_refund:{request_id}", order_id=order_id)
        if isinstance(e, ProviderNotConfigured):
            raise DomainError("Перегенерация кадра ещё не подключена. Токены возвращены.", code="not_connected", status=503)
        raise DomainError("Не получилось перегенерировать кадр. Токены возвращены.", code="regen_failed", status=500)
    with db.tx() as conn:
        conn.execute("UPDATE orders SET frames = ?, result_path = ? WHERE id = ? AND user_id = ?", (json.dumps(frames, ensure_ascii=False), sheet_path, order_id, user_id))
    storage.delete(old["path"])
    storage.delete(o["result_path"])
    return orders.public_order(orders.get_user_order(db, user_id, order_id))
