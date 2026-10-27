"""Клиент публичного API продавца IziMarket.

Документация: https://izi.market/settings/api/docs (копия — docs/api/).

Политика повторов:
* GET повторяется при сетевых сбоях, 5xx и 429;
* изменяющий запрос повторяется только при 429 (сервер его точно не выполнил)
  и, если у него есть Idempotency-Key, при сетевых сбоях;
* 401 не повторяется никогда — ключ надо перевыпустить.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from typing import Any, Iterator

import requests

from .exceptions import IziAPIError, NetworkError, RateLimitError, make_error
from .types import Balance, Order, Product, StockPage

logger = logging.getLogger("IziAPI")

BASE_URL = "https://api.izi.market/api/public/v1"
USER_AGENT = "IziMarketHub/1.0 (+https://t.me/fairydarkns)"


class Client:
    def __init__(self, api_key: str, base_url: str = BASE_URL, locale: str = "ru", timeout: float = 20,
                 proxy: str | None = None, max_retries: int = 3):
        if not api_key:
            raise ValueError("Не задан ключ API (izp_…)")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "Accept-Language": locale,
            "User-Agent": USER_AGENT,
        })
        if proxy:
            self.session.proxies = {"http": proxy, "https": proxy}
        self._lock = threading.Lock()
        #: последние значения заголовков лимитов
        self.rate_limit: dict[str, str] = {}

    # ------------------------------------------------------------------ транспорт

    def request(self, method: str, path: str, *, params: dict | None = None, json: Any = None,
                idempotency_key: str | None = None, files: dict | None = None) -> Any:
        """Выполняет запрос и возвращает ``data`` из конверта ответа."""
        method = method.upper()
        safe_to_retry_network = method == "GET" or idempotency_key is not None
        headers = {}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        if params:
            params = {k: v for k, v in params.items() if v is not None}

        attempt = 0
        while True:
            attempt += 1
            try:
                resp = self.session.request(method, self.base_url + path, params=params, json=json,
                                            files=files, headers=headers, timeout=self.timeout)
            except requests.RequestException as e:
                if safe_to_retry_network and attempt < self.max_retries:
                    logger.warning(f"{method} {path}: сетевой сбой ({e}), повтор {attempt}")
                    time.sleep(2 ** attempt)
                    continue
                raise NetworkError(f"{method} {path}: {e}") from e

            self._remember_limits(resp)
            try:
                body = resp.json()
            except ValueError:
                body = None

            if resp.ok and isinstance(body, dict) and body.get("status", True):
                return body.get("data")

            data = body.get("data") if isinstance(body, dict) else None
            data = data if isinstance(data, dict) else {}
            retry_after = _float(resp.headers.get("Retry-After")) or _float(data.get("retry_after"))
            err = make_error(resp.status_code, data.get("code"), data.get("message") or resp.text[:200],
                             data, retry_after)

            retryable = isinstance(err, RateLimitError) or (method == "GET" and resp.status_code >= 500
                                                             and resp.status_code != 503)
            if retryable and attempt < self.max_retries:
                wait = min(retry_after or 2 ** attempt, 60)
                logger.warning(f"{method} {path}: {err.code or resp.status_code}, жду {wait:.0f} с")
                time.sleep(wait)
                continue
            raise err

    def _remember_limits(self, resp: requests.Response) -> None:
        for k, v in resp.headers.items():
            if k.lower().startswith("x-ratelimit"):
                self.rate_limit[k] = v

    def get(self, path: str, **params) -> Any:
        return self.request("GET", path, params=params)

    @staticmethod
    def new_idempotency_key() -> str:
        return "imh-" + uuid.uuid4().hex

    # ------------------------------------------------------------------ ключ и аккаунт

    def get_me(self) -> dict:
        return self.get("/me")

    def get_account(self) -> dict:
        return self.get("/account")

    def get_balance(self) -> Balance:
        return Balance.from_dict(self.get("/balance"))

    # ------------------------------------------------------------------ каталог

    def get_catalog_tree(self) -> Any:
        return self.get("/catalog/tree")

    def get_subcategory_schema(self, subcategory: int | str) -> dict:
        return self.get(f"/catalog/subcategories/{subcategory}/schema")

    # ------------------------------------------------------------------ товары

    def list_products(self, page: int = 1, status: str | None = None, game: str | None = None,
                      search: str | None = None, sort: str | None = None) -> tuple[list[Product], bool]:
        data = self.get("/products", page=page, status=status, game=game, search=search, sort=sort)
        return [Product.from_dict(p) for p in data["items"]], bool(data.get("has_next_page"))

    def iter_products(self, **filters) -> Iterator[Product]:
        page = 1
        while True:
            items, has_next = self.list_products(page=page, **filters)
            yield from items
            if not has_next:
                return
            page += 1

    def get_product(self, product_id: str) -> Product:
        return Product.from_dict(self.get(f"/products/{product_id}"))

    def create_product(self, payload: dict, idempotency_key: str | None = None) -> Product:
        return Product.from_dict(self.request("POST", "/products", json=payload,
                                              idempotency_key=idempotency_key or self.new_idempotency_key()))

    def update_product(self, product_id: str, payload: dict) -> Product:
        return Product.from_dict(self.request("PATCH", f"/products/{product_id}", json=payload))

    def delete_product(self, product_id: str) -> Any:
        return self.request("DELETE", f"/products/{product_id}")

    def publish_product(self, product_id: str, locale: str | None = None) -> Product:
        body = {"locale": locale} if locale else None
        return Product.from_dict(self.request("POST", f"/products/{product_id}/publish", json=body))

    def unpublish_product(self, product_id: str) -> Product:
        return Product.from_dict(self.request("POST", f"/products/{product_id}/unpublish"))

    def set_product_price(self, product_id: str, price_minor: int, version: int | None = None) -> Product:
        if version is None:
            version = self.get_product(product_id).version
        return Product.from_dict(self.request("PUT", f"/products/{product_id}/price",
                                              json={"version": version, "price_minor": int(price_minor)}))

    def set_product_quantity(self, product_id: str, quantity: int, version: int | None = None) -> Product:
        if version is None:
            version = self.get_product(product_id).version
        return Product.from_dict(self.request("PUT", f"/products/{product_id}/quantity",
                                              json={"version": version, "quantity": int(quantity)}))

    def bulk_update_products(self, items: list[dict]) -> Any:
        return self.request("POST", "/products/bulk-update", json={"items": items})

    def add_product_variant(self, product_id: str, payload: dict) -> Any:
        return self.request("POST", f"/products/{product_id}/variants", json=payload)

    # группы
    def create_product_group(self, payload: dict) -> Any:
        return self.request("POST", "/products/groups", json=payload)

    def get_product_group(self, group_id: str) -> Any:
        return self.get(f"/products/groups/{group_id}")

    def replace_product_group(self, group_id: str, payload: dict) -> Any:
        return self.request("PUT", f"/products/groups/{group_id}", json=payload)

    def disband_product_group(self, group_id: str) -> Any:
        return self.request("DELETE", f"/products/groups/{group_id}")

    # ------------------------------------------------------------------ картинки

    def upload_image(self, path: str, idempotency_key: str | None = None) -> Any:
        with open(path, "rb") as f:
            return self.request("POST", "/media", files={"file": f},
                                idempotency_key=idempotency_key or self.new_idempotency_key())

    def get_image(self, upload_id: str) -> Any:
        return self.get(f"/media/{upload_id}")

    # ------------------------------------------------------------------ склад автовыдачи

    def list_stock(self, product_id: str, status: str | None = None, page: int = 1, per_page: int = 50,
                   q: str | None = None) -> StockPage:
        d = self.get(f"/products/{product_id}/stock", status=status, page=page, per_page=per_page, q=q)
        return StockPage(d["items"], bool(d.get("has_next_page")), int(d.get("available") or 0),
                         int(d.get("sold") or 0))

    def add_stock(self, product_id: str, items: list[str | dict], delimiter: str | None = None,
                  on_invalid: str = "reject", idempotency_key: str | None = None) -> dict:
        body: dict[str, Any] = {"items": items, "on_invalid": on_invalid}
        if delimiter is not None:
            body["delimiter"] = delimiter
        return self.request("POST", f"/products/{product_id}/stock", json=body,
                            idempotency_key=idempotency_key or self.new_idempotency_key())

    def bulk_delete_stock(self, product_id: str, ids: list[int]) -> Any:
        return self.request("POST", f"/products/{product_id}/stock/bulk-delete", json={"ids": ids})

    def delete_stock_item(self, product_id: str, item_id: int) -> Any:
        return self.request("DELETE", f"/products/{product_id}/stock/{item_id}")

    # ------------------------------------------------------------------ сделки

    def list_orders(self, status: str | None = None, created_from: str | None = None,
                    created_to: str | None = None, product_id: str | None = None,
                    updated_since: str | None = None, cursor: str | None = None,
                    limit: int = 50) -> tuple[list[Order], str | None]:
        d = self.get("/orders", status=status, created_from=created_from, created_to=created_to,
                     product_id=product_id, updated_since=updated_since, cursor=cursor, limit=limit)
        nxt = d.get("next_cursor") if d.get("has_next_page") else None
        return [Order.from_dict(o) for o in d["items"]], nxt

    def iter_orders(self, max_pages: int = 100, **filters) -> Iterator[Order]:
        cursor = None
        for _ in range(max_pages):
            items, cursor = self.list_orders(cursor=cursor, **filters)
            yield from items
            if not cursor:
                return

    def get_order(self, order_id: str) -> Order:
        return Order.from_dict(self.get(f"/orders/{order_id}"))

    def deliver_order(self, order_id: str, content: str | None = None, fields: dict | None = None) -> Order:
        """Выдать сделку. Выдача необратима; повторно не отправляется."""
        body: dict[str, Any] = {}
        if content:
            body["content"] = content[:2000]
        if fields:
            body["fields"] = fields
        return Order.from_dict(self.request("POST", f"/orders/{order_id}/deliver", json=body))

    # ------------------------------------------------------------------ аналитика

    def get_analytics(self, date_from: str | None = None, date_to: str | None = None,
                      metrics: str | None = None, sections: str | None = None) -> dict:
        return self.get("/analytics", **{"from": date_from, "to": date_to, "metrics": metrics,
                                         "sections": sections})

    def get_analytics_metrics(self) -> dict:
        return self.get("/analytics/metrics")

    # ------------------------------------------------------------------ вебхуки

    def get_webhook(self) -> dict | None:
        try:
            return self.get("/webhook")
        except IziAPIError as e:
            if e.status == 404:
                return None
            raise

    def put_webhook(self, url: str, events: list[str] | None = None, enabled: bool = True) -> dict:
        body: dict[str, Any] = {"url": url, "enabled": enabled}
        if events:
            body["events"] = events
        return self.request("PUT", "/webhook", json=body)

    def delete_webhook(self) -> Any:
        return self.request("DELETE", "/webhook")

    def ping_webhook(self) -> dict:
        return self.request("POST", "/webhook/ping")

    def list_webhook_deliveries(self, status: str | None = None, type: str | None = None,
                                page: int = 1) -> dict:
        return self.get("/webhook/deliveries", status=status, type=type, page=page)

    def get_webhook_delivery(self, delivery_id: str) -> dict:
        return self.get(f"/webhook/deliveries/{delivery_id}")

    def redeliver_webhook_delivery(self, delivery_id: str) -> Any:
        return self.request("POST", f"/webhook/deliveries/{delivery_id}/redeliver")


def _float(v: Any) -> float | None:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None
