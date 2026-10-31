"""Переменные в текстах бота.

Автовыдача и сообщения по заказу:
$username       — ник покупателя
$order_id       — id сделки
$order_link     — ссылка на сделку
$product_title  — название товара
$product_id     — id товара
$quantity       — сколько единиц куплено
$amount         — сумма сделки
$seller_amount  — сколько получит продавец
$date / $time   — текущие дата и время, $full_date — «31 октября 2026»
$product        — выдаваемые единицы товара из файла (каждая с новой строки)
$input_<key>    — что покупатель ввёл при покупке (например, $input_nick)
$param_<N>      — выбранный параметр по номеру группы (например, $param_12)

Сообщения чата (автоответчик, приветствие, заготовки):
$username, $chat_name, $chat_id, $order_id, $order_title, $order_link, $message_text,
$date, $time, $full_date

Если переменной нет (например, $order_title в личном диалоге), вместо неё подставляется пустота.
"""

from __future__ import annotations

import re
from datetime import datetime

from IziAPI.types import Chat, ChatMessage, Order

_INPUT_RE = re.compile(r"\$input_([A-Za-z0-9_\-]+)")
_PARAM_RE = re.compile(r"\$param_(\d+)")

MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября",
          "ноября", "декабря"]


def _time_values() -> dict[str, str]:
    now = datetime.now()
    return {
        "$date": now.strftime("%d.%m.%Y"),
        "$time": now.strftime("%H:%M"),
        "$full_date": f"{now.day} {MONTHS[now.month - 1]} {now.year}",
    }


def render(text: str, values: dict[str, str], extra: list[tuple[re.Pattern, callable]] = ()) -> str:
    """Подставляет переменные за один проход (подставленное не раскрывается повторно).
    Переменной без значения соответствует пустая строка."""
    text = text.replace("\\n", "\n")
    names = "|".join(re.escape(k) for k in sorted(values, key=len, reverse=True))
    patterns = [p.pattern for p, _ in extra] + ([names] if names else [])
    if not patterns:
        return text
    combined = re.compile("|".join(f"(?:{p})" for p in patterns))

    def value_of(m: re.Match) -> str:
        token = m.group(0)
        if token in values:
            return values[token]
        for pattern, fn in extra:
            pm = pattern.fullmatch(token)
            if pm:
                return fn(pm)
        return token

    return combined.sub(value_of, text)


def format_text(text: str, order: Order, goods: list[str] | None = None) -> str:
    values = {
        "$username": order.buyer.username or "покупатель",
        "$order_id": order.id,
        "$order_link": f"https://izi.market/orders/{order.id}",
        "$product_title": order.product_title or "",
        "$product_id": order.product_id or "",
        "$quantity": str(order.quantity),
        "$amount": str(order.amount) if order.amount else "",
        "$seller_amount": str(order.seller_amount) if order.seller_amount else "",
        "$product": "\n".join(goods or []),
        **_time_values(),
    }
    params = {str(p.get("group_id")): p for p in order.buyer.parameters}

    def _param(m: re.Match) -> str:
        p = params.get(m.group(1))
        if not p:
            return ""
        if p.get("value") not in (None, ""):
            return str(p["value"])
        return ", ".join(o.get("label_ru") or o.get("label_en") or "" for o in p.get("options") or [])

    return render(text, values, [(_INPUT_RE, lambda m: str(order.buyer.inputs.get(m.group(1), ""))),
                                 (_PARAM_RE, _param)])


def format_chat_text(text: str, chat: Chat, message: ChatMessage | None = None) -> str:
    values = {
        "$username": chat.counterpart.username or "покупатель",
        "$chat_name": chat.counterpart.username or "покупатель",
        "$chat_id": chat.id,
        "$order_id": chat.order_id or "",
        "$order_title": chat.order_title or "",
        "$order_link": f"https://izi.market/orders/{chat.order_id}" if chat.order_id else "",
        "$message_text": message.text if message else "",
        **_time_values(),
    }
    return render(text, values)
