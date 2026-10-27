"""Приёмник вебхуков IziMarket.

Слушает http на host:port (по умолчанию 127.0.0.1:8080). IziMarket шлёт вебхуки только на https,
поэтому наружу его выставляют через обратный прокси (nginx, Caddy) или туннель.
"""

from __future__ import annotations

import json
import logging
import threading
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import TYPE_CHECKING

from IziAPI import WebhookEvent, verify_signature

if TYPE_CHECKING:
    from hub import IziMarketHub

logger = logging.getLogger("IMH.webhook")

MAX_BODY = 1024 * 1024


class WebhookServer:
    def __init__(self, hub: IziMarketHub):
        self.hub = hub
        w = hub.MAIN_CFG["Webhook"]
        self.host = w["host"]
        self.port = int(w["port"])
        self.path = w["path"]
        self.secret = w["signingSecret"]
        self._seen: OrderedDict[str, None] = OrderedDict()
        self._seen_lock = threading.Lock()
        self.httpd: ThreadingHTTPServer | None = None

    def seen(self, event_id: str) -> bool:
        with self._seen_lock:
            if event_id in self._seen:
                return True
            self._seen[event_id] = None
            while len(self._seen) > 2000:
                self._seen.popitem(last=False)
            return False

    def start(self) -> None:
        if not self.secret:
            logger.error("Вебхуки включены, но не задан [Webhook] signingSecret (izs_…) — приёмник не запущен")
            return
        server = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt, *args):
                logger.debug(fmt % args)

            def _reply(self, code: int, text: str = "ok") -> None:
                body = text.encode()
                self.send_response(code)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                self._reply(200 if self.path == server.path else 404, "IziMarketHub")

            def do_POST(self):
                if self.path.split("?")[0] != server.path:
                    return self._reply(404, "not found")
                length = int(self.headers.get("Content-Length") or 0)
                if length <= 0 or length > MAX_BODY:
                    return self._reply(413, "bad length")
                raw = self.rfile.read(length)
                if not verify_signature(server.secret, self.headers.get("X-IziMarket-Timestamp"),
                                        self.headers.get("X-IziMarket-Signature"), raw):
                    logger.warning(f"Вебхук с неверной подписью от {self.client_address[0]}")
                    return self._reply(401, "bad signature")
                try:
                    event = WebhookEvent.from_dict(json.loads(raw))
                except (ValueError, AttributeError):
                    return self._reply(400, "bad json")
                event_id = self.headers.get("X-IziMarket-Event-Id") or event.id
                # отвечаем сразу: обработка идёт в фоне, а повтор доставки отсеется по event_id
                self._reply(200)
                if event.type == "ping" or server.seen(event_id):
                    return
                logger.info(f"Вебхук {event.type}")
                threading.Thread(target=server.hub.dispatch, args=("WEBHOOK_EVENT", event),
                                 name="webhook-event", daemon=True).start()

        self.httpd = ThreadingHTTPServer((self.host, self.port), Handler)
        threading.Thread(target=self.httpd.serve_forever, name="webhook", daemon=True).start()
        logger.info(f"Приёмник вебхуков слушает http://{self.host}:{self.port}{self.path}")

    def stop(self) -> None:
        if self.httpd:
            self.httpd.shutdown()
