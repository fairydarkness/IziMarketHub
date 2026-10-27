"""Встроенные обработчики: автовыдача, автодеактивация, синхронизация количества, пополнение склада."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from IziAPI import Order, Product
from IziAPI.exceptions import ConflictError, IziAPIError, NetworkError
from Utils.config_loader import is_true
from Utils.storage import unescape_item
from Utils.templates import format_text

if TYPE_CHECKING:
    from hub import IziMarketHub

logger = logging.getLogger("IMH.handlers")

REFILL_FAILED_DIR = os.path.join("storage", "refill_failed")


# ---------------------------------------------------------------------- автовыдача

def auto_delivery_handler(hub: IziMarketHub, order: Order) -> None:
    if order.status != "paid" or not hub.setting("autoDelivery"):
        return
    section = hub.find_ad_section(order.product_id, order.product_title)
    if not section:
        logger.debug(f"Сделка #{order.id[:8]}: для «{order.product_title}» автовыдача не настроена")
        return
    s = hub.AD_CFG[section]
    if is_true(s.get("disable")):
        logger.info(f"Сделка #{order.id[:8]}: автовыдача для «{section}» выключена")
        return

    product = None
    if order.product_id:
        try:
            product = hub.get_product(order.product_id)
        except IziAPIError as e:
            logger.warning(f"Не удалось прочитать товар {order.product_id}: {e}")
    if product and product.stock_managed:
        logger.info(f"Сделка #{order.id[:8]}: товар со склада площадки — его выдаёт IziMarket")
        return

    file_name = s.get("productsFileName")
    goods: list[str] = []
    if file_name:
        taken = hub.goods.take(file_name, order.quantity)
        if taken is None:
            left = hub.goods.count(file_name)
            reason = f"в файле {file_name} не хватает товара: нужно {order.quantity}, есть {left}"
            logger.warning(f"Сделка #{order.id[:8]}: {reason}")
            hub.dispatch("DELIVERY_FAILED", order, reason)
            return
        goods = [unescape_item(g) for g in taken]

    content = format_text(s.get("response") or "$product", order, goods)
    fields = _build_fields(s.get("fields"), goods)

    try:
        hub.deliver(order, content, fields, by_bot=True)
    except ConflictError as e:
        # сделку уже выдали руками, отменили или закрыли — товар остаётся у продавца
        _give_back(hub, file_name, taken if file_name else [])
        logger.warning(f"Сделка #{order.id[:8]} не выдана: {e.data.get('current_status') or e.code}")
        hub.dispatch("DELIVERY_FAILED", order, f"сделка уже в статусе {e.data.get('current_status') or e.code}")
        return
    except NetworkError as e:
        # ответа нет — проверяем, дошла ли выдача, прежде чем вернуть товар в файл
        outcome = _delivery_outcome(hub, order)
        if outcome == "delivered":
            logger.info(f"Сделка #{order.id[:8]} выдана (подтверждено повторным чтением)")
            hub.dispatch("ORDER_DELIVERED", order, content, True)
        elif outcome == "unknown":
            # товар в файл не возвращаем, чтобы не выдать его второй раз
            hub.dispatch("DELIVERY_FAILED", order, f"исход выдачи неизвестен ({e}) — проверьте сделку вручную. "
                                                   f"Снятый товар:\n{chr(10).join(goods)}")
            return
        else:
            _give_back(hub, file_name, taken if file_name else [])
            hub.dispatch("DELIVERY_FAILED", order, f"сеть: {e}")
            return
    except IziAPIError as e:
        _give_back(hub, file_name, taken if file_name else [])
        logger.error(f"Сделка #{order.id[:8]} не выдана: {e}")
        hub.dispatch("DELIVERY_FAILED", order, f"{e.code}: {e.message}")
        return

    if file_name and product:
        _after_goods_spent(hub, section, product, file_name)


def _build_fields(spec: str | None, goods: list[str]) -> dict | None:
    """``fields = login,password`` + строка ``kiwi:melon`` → {"login": "kiwi", "password": "melon"}."""
    if not spec or len(goods) != 1:
        return None
    keys = [k.strip() for k in spec.split(",") if k.strip()]
    parts = goods[0].split(":", len(keys) - 1)
    if len(parts) != len(keys):
        return None
    return dict(zip(keys, (p.strip() for p in parts)))


def _give_back(hub: IziMarketHub, file_name: str | None, raw_items: list[str]) -> None:
    if file_name and raw_items:
        hub.goods.give_back(file_name, raw_items)


def _delivery_outcome(hub: IziMarketHub, order: Order) -> str:
    """delivered / not_delivered / unknown — после выдачи без ответа сервера."""
    try:
        fresh = hub.client.get_order(order.id)
    except (IziAPIError, NetworkError):
        logger.error(f"Сделка #{order.id[:8]}: исход выдачи неизвестен, товар оставлен снятым — проверьте вручную")
        return "unknown"
    if fresh.status == "paid":
        return "not_delivered"
    hub.mark_order(fresh)
    return "delivered" if fresh.status in ("delivered", "completed") else "not_delivered"


def _after_goods_spent(hub: IziMarketHub, section: str, product: Product, file_name: str) -> None:
    s = hub.AD_CFG[section]
    left = hub.goods.count(file_name)
    if left == 0:
        if hub.setting("autoDisable") and not is_true(s.get("disableAutoDisable")):
            hub.disable_product(product, f"закончился товар в {file_name}")
        return
    if hub.setting("syncQuantity") and not product.stock_managed and product.quantity != min(left, 100000):
        try:
            hub.client.set_product_quantity(product.id, min(left, 100000))
            hub.forget_product(product.id)
        except IziAPIError as e:
            logger.warning(f"Не удалось обновить количество «{product.title}»: {e}")


# ---------------------------------------------------------------------- склад площадки

def refill_stock_all(hub: IziMarketHub) -> None:
    """Пополняет склад автовыдачи площадки из локальных файлов, если свободных единиц мало."""
    threshold = hub.MAIN_CFG.getint("StockRefill", "threshold")
    for section in hub.AD_CFG.sections():
        s = hub.AD_CFG[section]
        if is_true(s.get("disable")) or not is_true(s.get("stockRefill")) or not s.get("productsFileName"):
            continue
        pid = hub.section_product_id(section)
        if not pid:
            continue
        try:
            product = hub.get_product(pid, max_age=0)
        except IziAPIError as e:
            logger.warning(f"Пополнение: товар «{section}» недоступен: {e}")
            continue
        if not product.stock_managed or product.quantity > threshold:
            continue
        refill_stock(hub, product, s["productsFileName"])


def refill_stock(hub: IziMarketHub, product: Product, file_name: str) -> int:
    batch = min(hub.MAIN_CFG.getint("StockRefill", "batch"), 1000)
    items = hub.goods.take(file_name, min(batch, hub.goods.count(file_name)))
    if not items:
        if product.quantity == 0:
            logger.info(f"Пополнение «{product.title}»: файл {file_name} пуст")
        return 0
    key = hub.client.new_idempotency_key()
    try:
        res = hub.client.add_stock(product.id, items, on_invalid="skip", idempotency_key=key)
    except ConflictError as e:
        hub.goods.give_back(file_name, items)
        logger.error(f"Пополнение «{product.title}»: {e}")
        return 0
    except NetworkError as e:
        # исход неизвестен: единицы могли попасть на склад, в файл их не возвращаем
        _save_failed(file_name, items, f"сеть: {e}")
        logger.error(f"Пополнение «{product.title}»: нет ответа, {len(items)} строк отложены в {REFILL_FAILED_DIR}")
        return 0
    except IziAPIError as e:
        hub.goods.give_back(file_name, items)
        logger.error(f"Пополнение «{product.title}»: {e}")
        return 0

    rejected = res.get("rejected") or []
    if rejected:
        bad = [items[r["line"] - 1] for r in rejected if 0 < (r.get("line") or 0) <= len(items)]
        _save_failed(file_name, bad, ", ".join(sorted({r.get('reason', '?') for r in rejected})))
        logger.warning(f"Пополнение «{product.title}»: отклонено {len(rejected)} строк — в {REFILL_FAILED_DIR}")
    added = int(res.get("added") or 0)
    hub.forget_product(product.id)
    logger.info(f"Склад «{product.title}» пополнен на {added}, свободно {res.get('available')}")
    hub.dispatch("STOCK_REFILLED", product, added)
    return added


def _save_failed(file_name: str, items: list[str], reason: str) -> None:
    if not items:
        return
    os.makedirs(REFILL_FAILED_DIR, exist_ok=True)
    with open(os.path.join(REFILL_FAILED_DIR, file_name), "a", encoding="utf-8") as f:
        f.write(f"# {reason}\n")
        f.writelines(i + "\n" for i in items)


# ---------------------------------------------------------------------- вебхуки

def webhook_router(hub: IziMarketHub, event) -> None:
    """Вебхук — только сигнал: данные всё равно берутся опросом, так ничего не теряется."""
    if event.type.startswith("order."):
        hub.wake(orders=True)
    elif event.type in ("product.stock.low", "product.stock.depleted"):
        pid = (event.data.get("product") or {}).get("id")
        if pid:
            hub.forget_product(pid)
        hub.wake(refill=True)
    elif event.type.startswith("product."):
        pid = (event.data.get("product") or {}).get("id")
        if pid:
            hub.forget_product(pid)


def register_handlers(hub: IziMarketHub) -> None:
    hub.add_handler("NEW_ORDER", auto_delivery_handler)
    hub.add_handler("WEBHOOK_EVENT", webhook_router)
