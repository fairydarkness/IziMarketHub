"""Переменные в текстах автовыдачи.

$username       — ник покупателя
$order_id       — id сделки
$product_title  — название товара
$product_id     — id товара
$quantity       — сколько единиц куплено
$amount         — сумма сделки
$seller_amount  — сколько получит продавец
$date / $time   — текущие дата и время
$product        — выдаваемые единицы товара из файла (каждая с новой строки)
$input_<key>    — что покупатель ввёл при покупке (например, $input_nick)
$param_<N>      — выбранный параметр по номеру группы (например, $param_12)

В сообщениях чата (автоответчик, приветствие):
$username, $chat_id, $order_id, $order_title, $message_text, $date, $time
"""

from __future__ import annotations

import re
from datetime import datetime

from IziAPI.types import Chat, ChatMessage, Order

_INPUT_RE = re.compile(r"\$input_([A-Za-z0-9_\-]+)")
_PARAM_RE = re.compile(r"\$param_(\d+)")


def format_text(text: str, order: Order, goods: list[str] | None = None) -> str:
    now = datetime.now()
    values = {
        "$username": order.buyer.username or "покупатель",
        "$order_id": order.id,
        "$product_title": order.product_title or "",
        "$product_id": order.product_id or "",
        "$quantity": str(order.quantity),
        "$amount": str(order.amount) if order.amount else "",
        "$seller_amount": str(order.seller_amount) if order.seller_amount else "",
        "$date": now.strftime("%d.%m.%Y"),
        "$time": now.strftime("%H:%M"),
        "$product": "\n".join(goods or []),
    }
    text = text.replace("\\n", "\n")
    text = _INPUT_RE.sub(lambda m: str(order.buyer.inputs.get(m.group(1), "")), text)

    params = {str(p.get("group_id")): p for p in order.buyer.parameters}

    def _param(m: re.Match) -> str:
        p = params.get(m.group(1))
        if not p:
            return ""
        if p.get("value") not in (None, ""):
            return str(p["value"])
        return ", ".join(o.get("label_ru") or o.get("label_en") or "" for o in p.get("options") or [])

    text = _PARAM_RE.sub(_param, text)
    # длинные имена первыми, чтобы $product не съел $product_title
    for key in sorted(values, key=len, reverse=True):
        text = text.replace(key, values[key])
    return text


def format_chat_text(text: str, chat: Chat, message: ChatMessage | None = None) -> str:
    now = datetime.now()
    values = {
        "$username": chat.counterpart.username or "покупатель",
        "$chat_id": chat.id,
        "$order_id": chat.order_id or "",
        "$order_title": chat.order_title or "",
        "$message_text": message.text if message else "",
        "$date": now.strftime("%d.%m.%Y"),
        "$time": now.strftime("%H:%M"),
    }
    text = text.replace("\\n", "\n")
    # один проход: подставленный текст сообщения не раскрывается повторно
    pattern = "|".join(re.escape(k) for k in sorted(values, key=len, reverse=True))
    return re.sub(pattern, lambda m: values[m.group(0)], text)
