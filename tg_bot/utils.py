"""Пароль доступа к Telegram-боту и форматирование сообщений."""

from __future__ import annotations

import hashlib
import hmac
import os
from html import escape

from IziAPI import Order, Product


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
