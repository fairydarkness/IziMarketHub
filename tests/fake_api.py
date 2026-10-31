"""Поддельное API IziMarket для тестов: хранит сделки и товары в памяти."""

from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PREFIX = "/api/public/v1"


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def money(minor: int) -> dict:
    return {"amount_minor": minor, "currency": "RUB"}


class FakeAPI:
    def __init__(self):
        self.orders: dict[str, dict] = {}
        self.products: dict[str, dict] = {}
        self.stock: dict[str, list[dict]] = {}
        self.calls: list[tuple[str, str, dict | None]] = []
        self.deliver_status: int | None = None  # подменить ответ выдачи
        self.chats: dict[str, dict] = {}
        self.messages: dict[str, list[dict]] = {}
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        self.url = f"http://127.0.0.1:{self.httpd.server_port}{PREFIX}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()

    # --- наполнение
    def add_product(self, pid: str, title: str, stock: bool = False, quantity: int = 10, status: str = "active"):
        self.products[pid] = {"id": pid, "title": title, "status": status, "version": 1, "price": money(10000),
                              "quantity": quantity, "delivery_mode": "stock" if stock else "manual",
                              "auto_delivery": stock, "stock_managed": stock, "sales": 0, "deleted": False}
        self.stock[pid] = []

    def add_order(self, oid: str, pid: str, quantity: int = 1, status: str = "paid", username: str = "kiwi"):
        self.orders[oid] = {"id": oid, "status": status, "product_id": pid, "quantity": quantity,
                            "amount": money(10000), "seller_amount": money(9000),
                            "product_title": self.products[pid]["title"], "created_at": now(),
                            "updated_at": now(), "buyer": {"id": "b1", "username": username,
                                                           "inputs": {"nick": "kiwi_game"}, "parameters": []}}

    def add_chat(self, cid: str, username: str = "kiwi", order_id: str | None = None):
        self.chats[cid] = {"id": cid, "type": "order" if order_id else "direct", "created_at": now(),
                           "counterpart": {"id": "b1", "number": 1, "username": username, "verified_seller": False},
                           "order": {"id": order_id, "title": "Robux", "role": "seller"} if order_id else None,
                           "last_seq": 0, "last_read_seq": 0, "counterpart_last_read_seq": 0, "unread_count": 0,
                           "last_message": None, "last_message_at": now()}
        self.messages[cid] = []

    def add_message(self, cid: str, text: str, author: str = "counterpart", client_message_id: str | None = None,
                    created_at: str | None = None) -> dict:
        c = self.chats[cid]
        c["last_seq"] += 1
        m = {"id": f"m{cid}{c['last_seq']}", "seq": c["last_seq"], "type": "text", "author": author,
             "staff_role": None, "text": text, "images": [], "attachments": [], "reply_to": None,
             "automatic": False, "deleted": False, "redacted": False, "withheld": False, "visibility": "all",
             "system": None, "read_by_counterpart": None, "client_message_id": client_message_id,
             "created_at": created_at or now()}
        self.messages[cid].append(m)
        c["last_message"] = m
        c["last_message_at"] = m["created_at"]
        if author == "counterpart":
            c["unread_count"] += 1
        return m

    # --- сервер
    def _handler(self):
        api = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _send(self, code, data, ok=True):
                body = json.dumps({"data": data, "status": ok}).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _err(self, code, err, **extra):
                self._send(code, {"message": err, "code": err, **extra}, ok=False)

            def _body(self):
                n = int(self.headers.get("Content-Length") or 0)
                return json.loads(self.rfile.read(n)) if n else None

            def _route(self, method):
                path, _, qs = self.path.partition("?")
                path = path[len(PREFIX):]
                params = dict(p.split("=", 1) for p in qs.split("&") if "=" in p)
                from urllib.parse import unquote
                params = {k: unquote(v) for k, v in params.items()}
                body = self._body() if method != "GET" else None
                api.calls.append((method, path, body))
                if self.headers.get("Authorization") != "Bearer izp_test":
                    return self._err(401, "public_api_key_invalid")

                if path == "/me":
                    return self._send(200, {"user_id": "u1", "username": "shop", "key": {
                        "prefix": "izp_test", "scopes": ["orders:read", "orders:write", "products:read",
                                                         "products:write", "stock:read", "stock:write",
                                                         "chats:read", "chats:write"],
                        "expires_at": "2030-01-01T00:00:00+00:00"}})
                if path == "/balance":
                    return self._send(200, {"balance": money(170000), "held": money(5000),
                                            "available": money(165000), "spend_only": money(0), "currency": "RUB"})
                if path == "/analytics/metrics":
                    return self._send(200, {"metrics": [{"key": "earned", "label": "К получению"},
                                                        {"key": "rating", "label": "Рейтинг"}]})
                if path == "/analytics":
                    # формы как у настоящего API: не только деньги
                    return self._send(200, {"period": {"from": "2026-10-21", "to": "2026-10-27"},
                                            "current": {"earned": money(71100), "sales": 3, "rating": {"average": 4.9, "reviews_count": 12},
                                                        "dispute_rate": 0.125, "margin": None, "views": {"total": 40}},
                                            "previous": {"earned": money(0), "sales": 0}})
                if path == "/orders":
                    items = list(api.orders.values())
                    if "status" in params:
                        items = [o for o in items if o["status"] == params["status"]]
                    if "created_from" in params:
                        cf = datetime.fromisoformat(params["created_from"]).replace(tzinfo=timezone.utc)
                        items = [o for o in items if datetime.fromisoformat(o["created_at"]) >= cf]
                    if "updated_since" in params:
                        since = datetime.fromisoformat(params["updated_since"])
                        items = [o for o in items if datetime.fromisoformat(o["updated_at"]) >= since]
                    return self._send(200, {"items": items, "has_next_page": False, "next_cursor": None})
                m = re.fullmatch(r"/orders/([^/]+)(/deliver)?", path)
                if m:
                    o = api.orders.get(m.group(1))
                    if not o:
                        return self._err(404, "order_not_found")
                    if m.group(2):
                        if api.deliver_status:
                            return self._err(api.deliver_status, "order_state_invalid", current_status="cancelled")
                        if o["status"] != "paid":
                            return self._err(409, "order_state_invalid", current_status=o["status"])
                        o.update(status="delivered", updated_at=now(), delivered=body)
                    return self._send(200, o)
                if path == "/chats":
                    items = sorted(api.chats.values(), key=lambda c: (c["last_message_at"], c["last_seq"]),
                                   reverse=True)
                    if "order_id" in params:
                        items = [c for c in items if (c["order"] or {}).get("id") == params["order_id"]]
                    return self._send(200, {"items": items, "has_next_page": False, "next_cursor": None})
                m = re.fullmatch(r"/chats/([^/]+)(/messages|/read)?", path)
                if m:
                    c = api.chats.get(m.group(1))
                    if not c:
                        return self._err(404, "conversation_not_found")
                    if m.group(2) == "/messages" and method == "POST":
                        if "Idempotency-Key" not in self.headers:
                            return self._err(400, "no_idempotency_key")
                        msg = api.add_message(c["id"], body.get("text", ""), "me", body.get("client_message_id"))
                        return self._send(201, msg)
                    if m.group(2) == "/messages":
                        after = int(params.get("after_seq", 0))
                        items = [x for x in api.messages[c["id"]] if x["seq"] > after]
                        return self._send(200, {"items": items, "has_next_page": False, "next_cursor": None})
                    if m.group(2) == "/read":
                        c["unread_count"] = 0
                        return self._send(200, {"last_read_seq": c["last_seq"], "unread_count": 0})
                    return self._send(200, {**c, "can_write": True, "write_blocked_reason": None})
                if path == "/products":
                    return self._send(200, {"items": list(api.products.values()), "has_next_page": False})
                m = re.fullmatch(r"/products/([^/]+)(/[a-z]+)?", path)
                if m:
                    p = api.products.get(m.group(1))
                    if not p:
                        return self._err(404, "product_not_found")
                    action = m.group(2)
                    if action == "/unpublish":
                        p["status"] = "hidden"
                    elif action == "/publish":
                        p["status"] = "active"
                    elif action == "/quantity":
                        p["quantity"] = body["quantity"]
                    elif action == "/stock" and method == "POST":
                        items = body["items"]
                        api.stock[p["id"]].extend(items)
                        p["quantity"] += len(items)
                        return self._send(201, {"added": len(items), "available": p["quantity"], "rejected": []})
                    return self._send(200, p)
                return self._err(404, "not_found")

            def do_GET(self):
                self._route("GET")

            def do_POST(self):
                self._route("POST")

            def do_PUT(self):
                self._route("PUT")

        return H
