"""Типы данных публичного API IziMarket.

Объекты — тонкие обёртки над словарями ответа: нужные поля разобраны,
весь ответ лежит в ``raw``, чтобы плагины могли читать новые поля API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@dataclass(frozen=True)
class Money:
    amount_minor: int
    currency: str = "RUB"

    @classmethod
    def from_dict(cls, d: dict | None) -> Money | None:
        if not d:
            return None
        return cls(int(d.get("amount_minor", 0)), d.get("currency", "RUB"))

    @property
    def amount(self) -> float:
        return self.amount_minor / 100

    def __str__(self) -> str:
        sign = {"RUB": "₽", "USD": "$", "EUR": "€"}.get(self.currency, self.currency)
        rub, kop = divmod(abs(self.amount_minor), 100)
        s = f"{rub:,}".replace(",", " ")
        if kop:
            s += f",{kop:02d}"
        return f"{'-' if self.amount_minor < 0 else ''}{s} {sign}"


class OrderStatus(str, Enum):
    PAID = "paid"
    DELIVERED = "delivered"
    DISPUTED = "disputed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


ORDER_STATUS_RU = {
    "paid": "оплачена",
    "delivered": "выдана",
    "disputed": "спор",
    "completed": "завершена",
    "cancelled": "отменена",
    "refunded": "возврат",
}


@dataclass
class Buyer:
    id: str | None
    username: str | None
    inputs: dict = field(default_factory=dict)
    parameters: list = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict | None) -> Buyer:
        d = d or {}
        return cls(d.get("id"), d.get("username"), d.get("inputs") or {}, d.get("parameters") or [])


@dataclass
class Order:
    id: str
    status: str
    product_id: str | None
    product_title: str | None
    quantity: int
    amount: Money | None
    seller_amount: Money | None
    profit: Money | None
    buyer: Buyer
    created_at: datetime | None
    updated_at: datetime | None
    deliver_due_at: datetime | None
    raw: dict

    @classmethod
    def from_dict(cls, d: dict) -> Order:
        return cls(
            id=d["id"],
            status=d.get("status", ""),
            product_id=d.get("product_id"),
            product_title=d.get("product_title"),
            quantity=int(d.get("quantity") or 1),
            amount=Money.from_dict(d.get("amount")),
            seller_amount=Money.from_dict(d.get("seller_amount")),
            profit=Money.from_dict(d.get("profit")),
            buyer=Buyer.from_dict(d.get("buyer")),
            created_at=parse_dt(d.get("created_at")),
            updated_at=parse_dt(d.get("updated_at")),
            deliver_due_at=parse_dt(d.get("deliver_due_at")),
            raw=d,
        )

    @property
    def status_ru(self) -> str:
        return ORDER_STATUS_RU.get(self.status, self.status)

    def parameter_values(self) -> dict[str, str]:
        """Выбранные покупателем параметры: заголовок → значение."""
        out = {}
        for p in self.buyer.parameters:
            title = p.get("title_ru") or p.get("title_en") or str(p.get("group_id"))
            if p.get("value") not in (None, ""):
                out[title] = str(p["value"])
            elif p.get("options"):
                out[title] = ", ".join(o.get("label_ru") or o.get("label_en") or "" for o in p["options"])
        return out


PRODUCT_STATUS_RU = {
    "draft": "черновик",
    "pending": "на модерации",
    "active": "в продаже",
    "rejected": "отклонён",
    "hidden": "снят",
}


@dataclass
class Product:
    id: str
    title: str
    status: str
    version: int
    price: Money | None
    quantity: int
    delivery_mode: str | None
    auto_delivery: bool
    stock_managed: bool
    sales: int
    deleted: bool
    url: str | None
    raw: dict

    @classmethod
    def from_dict(cls, d: dict) -> Product:
        return cls(
            id=d["id"],
            title=d.get("title") or "",
            status=d.get("status", ""),
            version=int(d.get("version") or 1),
            price=Money.from_dict(d.get("price")),
            quantity=int(d.get("quantity") or 0),
            delivery_mode=d.get("delivery_mode"),
            auto_delivery=bool(d.get("auto_delivery")),
            stock_managed=bool(d.get("stock_managed")),
            sales=int(d.get("sales") or 0),
            deleted=bool(d.get("deleted")),
            url=d.get("url") or f"https://izi.market/products/{d['id']}",
            raw=d,
        )

    @property
    def status_ru(self) -> str:
        return PRODUCT_STATUS_RU.get(self.status, self.status)


@dataclass
class StockPage:
    items: list[dict]
    has_next_page: bool
    available: int
    sold: int


@dataclass
class Balance:
    balance: Money
    held: Money
    available: Money
    spend_only: Money | None

    @classmethod
    def from_dict(cls, d: dict) -> Balance:
        return cls(Money.from_dict(d["balance"]), Money.from_dict(d["held"]),
                   Money.from_dict(d["available"]), Money.from_dict(d.get("spend_only")))


@dataclass
class WebhookEvent:
    id: str
    type: str
    api_version: str | None
    occurred_at: datetime | None
    data: dict

    @classmethod
    def from_dict(cls, d: dict) -> WebhookEvent:
        return cls(d.get("id", ""), d.get("type", ""), d.get("api_version"),
                   parse_dt(d.get("occurred_at")), d.get("data") or {})
