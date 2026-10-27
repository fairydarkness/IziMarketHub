"""Пример плагина IziMarketHub.

Файлы, чьё имя начинается с «_», не загружаются. Чтобы включить пример,
скопируйте его в plugins/ под другим именем и поменяйте UUID.

Обработчик получает hub (ядро IziMarketHub) и аргументы события — см. EVENTS в hub.py.
"""

from __future__ import annotations

import logging

NAME = "Пример плагина"
VERSION = "1.0"
DESCRIPTION = "Пишет в лог о каждой новой сделке и шлёт сообщение в Telegram при споре."
CREDITS = "@fairydarkns"
UUID = "4f1b9c2e-0000-4000-8000-000000000000"

logger = logging.getLogger(f"IMH.plugin.{NAME}")


def on_new_order(hub, order):
    logger.info(f"Новая сделка от {order.buyer.username}: {order.product_title}, {order.amount}")


def on_status(hub, order, old_status):
    if order.status == "disputed" and hub.tg:
        hub.tg.notify("status", f"⚠️ Открыт спор по сделке #{order.id[:8]} — зайдите на сайт")


BIND_TO_NEW_ORDER = [on_new_order]
BIND_TO_ORDER_STATUS_CHANGED = [on_status]
