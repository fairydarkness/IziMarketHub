"""Проверка подписи вебхуков IziMarket.

Подпись: HMAC-SHA256 от ``<X-IziMarket-Timestamp>.<сырое тело>`` ключом подписи (izs_…), hex.
Заголовок ``X-IziMarket-Signature``: ``v1=<hex>``; сутки после смены ключа — две через запятую.
Запросы старше 5 минут отклоняются, повторы отсеиваются по ``X-IziMarket-Event-Id``.
"""

from __future__ import annotations

import hashlib
import hmac
import time

EVENT_TYPES = [
    "product.status_changed", "product.moderation.approved", "product.moderation.rejected",
    "product.removed", "product.restored", "product.needs_update", "product.relocated",
    "product.price_changed", "product.stock.depleted", "product.stock.low", "product.stock.replenished",
    "order.created", "order.delivered", "order.redelivered", "order.disputed", "order.completed",
    "order.refunded", "order.payout_released", "order.delivery_requested",
]

MAX_AGE = 300


def sign(secret: str, timestamp: str | int, body: bytes) -> str:
    msg = str(timestamp).encode() + b"." + body
    return hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()


def verify_signature(secret: str, timestamp: str | None, signature_header: str | None, body: bytes,
                     now: float | None = None, max_age: int = MAX_AGE) -> bool:
    if not (secret and timestamp and signature_header):
        return False
    try:
        ts = int(timestamp)
    except ValueError:
        return False
    if abs((now or time.time()) - ts) > max_age:
        return False
    expected = sign(secret, timestamp, body)
    for part in signature_header.split(","):
        part = part.strip()
        if part.startswith("v1=") and hmac.compare_digest(part[3:], expected):
            return True
    return False
