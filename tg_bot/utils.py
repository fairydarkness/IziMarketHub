"""Пароль доступа к Telegram-боту и форматирование сообщений."""

from __future__ import annotations

import hashlib
import hmac
import os
from html import escape

from IziAPI import Chat, ChatMessage, Order, Product


def hash_password(password: str) -> str:
    salt = os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 200_000).hex()
    return f"pbkdf2${salt}${digest}"


def check_password(password: str, stored: str) -> bool:
    try:
        algo, salt, digest = stored.split("$")
    except ValueError:
        return False
    if algo != "pbkdf2":
        return False
    calc = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 200_000).hex()
    return hmac.compare_digest(calc, digest)


def b(text) -> str:
    return f"<b>{escape(str(text))}</b>"


def code(text) -> str:
    return f"<code>{escape(str(text))}</code>"


def order_text(order: Order, title: str = "🛒 Новая сделка") -> str:
    lines = [
        f"{title} {code('#' + order.id[:8])}",
        f"📦 {b(order.product_title or order.product_id)} × {order.quantity}",
        f"💵 {escape(str(order.amount))}  →  вам {escape(str(order.seller_amount))}",
        f"👤 {b(order.buyer.username or '—')}",
        f"📌 Статус: {escape(order.status_ru)}",
    ]
    if order.buyer.inputs:
        lines.append("✏️ Ввод покупателя: " + ", ".join(f"{escape(k)}={code(v)}"
                                                       for k, v in order.buyer.inputs.items()))
    params = order.parameter_values()
    if params:
        lines.append("⚙️ " + "; ".join(f"{escape(k)}: {escape(v)}" for k, v in params.items()))
    if order.deliver_due_at and order.status == "paid":
        lines.append(f"⏰ Выдать до {order.deliver_due_at.astimezone().strftime('%d.%m %H:%M')}")
    lines.append(code(order.id))
    return "\n".join(lines)


def product_line(p: Product) -> str:
    mode = "склад" if p.stock_managed else "вручную"
    return f"{escape(p.title)} — {escape(str(p.price))}, {p.quantity} шт., {escape(p.status_ru)}, {mode}"


def truncate(text: str, limit: int = 3900) -> str:
    return text if len(text) <= limit else text[:limit] + "\n…"


def author_label(chat: Chat, msg: ChatMessage) -> str:
    if msg.by_me:
        return "🧑‍💼 Вы" + (" (авто)" if msg.automatic else "")
    if msg.by_counterpart:
        return f"👤 {b(chat.username)}"
    if msg.by_staff:
        return f"🛡 {b(msg.raw.get('staff_role') or 'Поддержка')}"
    return "ℹ️ Система"


def message_body(msg: ChatMessage, limit: int = 1500) -> str:
    if msg.deleted:
        return "<i>сообщение удалено</i>"
    if msg.withheld:
        return "<i>сообщение скрыто (только арбитру)</i>"
    parts = []
    text = msg.text.replace("\ufffc", "").strip()
    if text:
        parts.append(escape(text[:limit]) + ("…" if len(text) > limit else ""))
    if msg.type not in ("text", "image") and not text:
        parts.append(f"<i>{escape(msg.type)}</i>")
    for i, img in enumerate(msg.images, 1):
        url = img.get("url") if isinstance(img, dict) else img if isinstance(img, str) else None
        parts.append(f'🖼 <a href="{escape(url)}">картинка {i}</a>' if url else "🖼 картинка")
    if msg.raw.get("attachments"):
        parts.append(f"📎 вложений: {len(msg.raw['attachments'])}")
    return "\n".join(parts) or "<i>пусто</i>"


def chat_title(chat: Chat) -> str:
    where = f" · заказ «{escape((chat.order_title or '')[:40])}»" if chat.type == "order" else ""
    return f"💬 {b(chat.username)}{where}"


def notify_line(chat: Chat, msg: ChatMessage) -> str:
    """Строка уведомления: «👤 ник: текст» — ник жирным курсивом, текст моноширинным."""
    if msg.by_me:
        who = "🫵 Вы"
    elif msg.by_counterpart:
        who = f"👤 {chat.username}"
    elif msg.by_staff:
        who = f"🛡 {msg.raw.get('staff_role') or 'Поддержка'}"
    else:
        who = "ℹ️ Система"
    head = f"<i><b>{escape(who)}:</b></i>"
    if msg.deleted:
        return f"{head} <i>сообщение удалено</i>"
    if msg.withheld:
        return f"{head} <i>сообщение скрыто (только арбитру)</i>"
    text = msg.text.replace("\ufffc", "").strip()
    parts = [f"<code>{escape(text[:1500])}</code>" if text else ""]
    for i, img in enumerate(msg.images, 1):
        url = img.get("url") if isinstance(img, dict) else img if isinstance(img, str) else None
        parts.append(f'<a href="{escape(url)}">🖼 картинка {i}</a>' if url else "🖼 картинка")
    if msg.raw.get("attachments"):
        parts.append(f"📎 вложений: {len(msg.raw['attachments'])}")
    return head + " " + " ".join(p for p in parts if p)
