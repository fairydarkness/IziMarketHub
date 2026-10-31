"""Встроенные обработчики: автовыдача, автодеактивация, синхронизация количества, пополнение склада,
автоответчик, приветствие и ответы в чат заказа."""

from __future__ import annotations

import logging
import os
import threading
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from IziAPI import Chat, ChatMessage, Order, Product
from IziAPI.types import parse_dt
from IziAPI.exceptions import ConflictError, IziAPIError, NetworkError
from Utils.config_loader import is_true
from Utils.storage import unescape_item
from Utils.templates import format_chat_text, format_text

if TYPE_CHECKING:
    from hub import IziMarketHub

logger = logging.getLogger("IMH.handlers")

REFILL_FAILED_DIR = os.path.join("storage", "refill_failed")


# ---------------------------------------------------------------------- автовыдача

def auto_delivery_handler(hub: IziMarketHub, order: Order) -> None:
    if order.status != "paid" or not hub.setting("autoDelivery"):
        return
    if hub.blocked(order.buyer.username, "Delivery"):
        logger.info(f"Сделка #{order.id[:8]}: {order.buyer.username} в чёрном списке — автовыдача пропущена")
        hub.dispatch("DELIVERY_FAILED", order, "покупатель в чёрном списке")
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


# ---------------------------------------------------------------------- чаты

def find_command(hub: IziMarketHub, text: str) -> str | None:
    """Секция автоответчика для текста: точное совпадение команды (без регистра) или вхождение,
    если у команды contains = 1. Несколько команд в одной секции — через |."""
    text = " ".join(text.lower().split())
    if not text:
        return None
    for section in hub.AR_CFG.sections():
        s = hub.AR_CFG[section]
        if is_true(s.get("disable")):
            continue
        for cmd in section.split("|"):
            cmd = " ".join(cmd.lower().split())
            if cmd and (text == cmd or (is_true(s.get("contains")) and cmd in text)):
                return section
    return None


def _send_safe(hub: IziMarketHub, chat_id: str, text: str, what: str) -> bool:
    """Отправка с $sleep/$photo. Текст с паузами уходит в фоне, чтобы не держать опрос чатов."""
    def run() -> bool:
        try:
            return bool(hub.send_text(chat_id, text))
        except (IziAPIError, NetworkError) as e:
            logger.warning(f"Чат {chat_id[:8]}: {what} не отправлено: {e}")
            return False

    if "$sleep=" in text:
        threading.Thread(target=run, name=f"send-{chat_id[:8]}", daemon=True).start()
        return True
    return run()


def auto_response_handler(hub: IziMarketHub, chat: Chat, msg: ChatMessage) -> None:
    if not msg.by_counterpart or not msg.text or not hub.chat_setting("autoResponse"):
        return
    section = find_command(hub, msg.text)
    if not section:
        return
    if hub.blocked(chat.counterpart.username, "Response"):
        logger.info(f"Чат {chat.id[:8]}: {chat.username} в чёрном списке — автоответ пропущен")
        return
    s = hub.AR_CFG[section]
    logger.info(f"Чат {chat.id[:8]}: команда «{section}» от {chat.username}")
    if s.get("response"):
        sent = _send_safe(hub, chat.id, format_chat_text(s["response"], chat, msg), f"ответ на «{section}»")
        if sent and hub.chat_setting("markReadAfterResponse"):
            try:
                hub.client.mark_chat_read(chat.id)
            except (IziAPIError, NetworkError):
                pass
    if is_true(s.get("telegramNotification")) and hub.tg:
        hub.tg.on_command(chat, msg, section, s.get("notificationText") or "")


def is_first_contact(chat: Chat, messages: list[ChatMessage], first: ChatMessage) -> bool:
    """Собеседник пишет впервые: чат новый для бота, создан недавно, и до этого сообщения в нём
    не было ничьих слов (бот видит чат впервые, значит, в messages вся его история)."""
    if not chat.is_new:
        return False
    created = parse_dt(chat.raw.get("created_at"))
    if created and (first.created_at or datetime.now(timezone.utc)) - created > timedelta(days=1):
        return False
    return not any((m.by_me or m.by_counterpart) for m in messages if m.seq < first.seq)


def greetings_handler(hub: IziMarketHub, chat: Chat, messages: list[ChatMessage]) -> None:
    """Приветствие тому, кто пишет впервые; если greetingsNewOnly = 0 — ещё и тому,
    кто не писал дольше greetingsCooldown дней."""
    if not hub.chat_setting("greetings") or not hub.chats_available:
        return
    if chat.type == "order" and not hub.chat_setting("greetingsOrderChats"):
        return
    first = next((m for m in messages if m.by_counterpart), None)
    if not first or any(m.by_me for m in messages if m.seq < first.seq):
        return
    if find_command(hub, first.text):
        return  # на команду отвечает автоответчик
    if hub.blocked(chat.counterpart.username, "Response"):
        return
    cooldown = timedelta(days=hub.MAIN_CFG.getint("Chat", "greetingsCooldown"))
    now = datetime.now(timezone.utc)
    greeted = (hub.store.get("greeted") or {}).get(chat.id)
    if hub.chat_setting("greetingsNewOnly"):
        if greeted or not is_first_contact(chat, messages, first):
            return
    else:
        if greeted and now - datetime.fromisoformat(greeted) < cooldown:
            return
        if not is_first_contact(chat, messages, first):
            prev = chat.prev_message_at
            if prev is None or (first.created_at or now) - prev < cooldown:
                return
    text = hub.MAIN_CFG.get("Chat", "greetingsText")
    if text and _send_safe(hub, chat.id, format_chat_text(text, chat, first), "приветствие"):
        hub.store.update("greeted", lambda old: _prune_dates({**(old or {}), chat.id: now.isoformat()}, 400))


def _prune_dates(d: dict, days: int = 60) -> dict:
    limit = datetime.now(timezone.utc) - timedelta(days=days)
    return {k: v for k, v in d.items() if datetime.fromisoformat(v) >= limit}


def _order_reply(hub: IziMarketHub, order: Order, key: str) -> None:
    """Ответ в чат заказа (новый заказ / подтверждение). Чат появляется не сразу — ждём в фоне."""
    if not hub.chat_setting("enabled") or not hub.chat_setting(key) or not hub.chats_available:
        return
    if hub.blocked(order.buyer.username, "Response"):
        return
    done_key = f"{key}:{order.id}"
    if done_key in (hub.store.get("order_replies") or {}):
        return
    text = format_text(hub.MAIN_CFG.get("Chat", f"{key}Text"), order)
    if not text.strip():
        return

    def run():
        try:
            chat = hub.find_order_chat(order.id)
        except (IziAPIError, NetworkError) as e:
            logger.warning(f"Сделка #{order.id[:8]}: чат не найден: {e}")
            return
        if not chat:
            logger.warning(f"Сделка #{order.id[:8]}: чат заказа так и не появился — сообщение не отправлено")
            return
        if _send_safe(hub, chat.id, text, "сообщение по заказу"):
            hub.store.update("order_replies", lambda old: _prune_dates(
                {**(old or {}), done_key: datetime.now(timezone.utc).isoformat()}))

    threading.Thread(target=run, name=f"order-reply-{order.id[:8]}", daemon=True).start()


def new_order_reply_handler(hub: IziMarketHub, order: Order) -> None:
    _order_reply(hub, order, "newOrderReply")


def order_confirm_reply_handler(hub: IziMarketHub, order: Order, old_status: str) -> None:
    if order.status == "completed":
        _order_reply(hub, order, "orderConfirmReply")


# ---------------------------------------------------------------------- вебхуки

def webhook_router(hub: IziMarketHub, event) -> None:
    """Вебхук — только сигнал: данные всё равно берутся опросом, так ничего не теряется."""
    if event.type.startswith("order."):
        hub.wake(orders=True)
    elif event.type.startswith("message."):
        hub.wake(chats=True)
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
    hub.add_handler("NEW_ORDER", new_order_reply_handler)
    hub.add_handler("ORDER_STATUS_CHANGED", order_confirm_reply_handler)
    hub.add_handler("NEW_MESSAGE", auto_response_handler)
    hub.add_handler("NEW_MESSAGES", greetings_handler)
    hub.add_handler("WEBHOOK_EVENT", webhook_router)
