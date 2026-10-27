"""Ядро IziMarketHub: опрос сделок, события, плагины, фоновые задачи."""

from __future__ import annotations

import importlib.util
import logging
import os
import sys
import threading
import time
import traceback
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Callable

from IziAPI import Client, Order, Product
from IziAPI.exceptions import InvalidKeyError, IziAPIError, NetworkError
from Utils import config_loader as cfg_loader
from Utils.storage import GoodsStorage, JSONStore

if TYPE_CHECKING:
    from tg_bot.bot import TGBot

logger = logging.getLogger("IMH")

VERSION = "1.0.0"
AUTHOR = "@fairydarkns"
AUTHOR_LINK = "https://t.me/fairydarkns"

# Имена событий. Плагин подписывается списком BIND_TO_<ИМЯ> = [функции].
EVENTS = [
    "PRE_INIT",                # (hub)
    "POST_INIT",               # (hub)
    "PRE_START",               # (hub)
    "POST_START",              # (hub)
    "PRE_STOP",                # (hub)
    "NEW_ORDER",               # (hub, order: Order)
    "ORDER_STATUS_CHANGED",    # (hub, order: Order, old_status: str)
    "ORDER_DELIVERED",         # (hub, order: Order, content: str, by_bot: bool)
    "DELIVERY_FAILED",         # (hub, order: Order, reason: str)
    "PRODUCT_DISABLED",        # (hub, product: Product, reason: str)
    "PRODUCT_RESTORED",        # (hub, product: Product)
    "STOCK_REFILLED",          # (hub, product: Product, added: int)
    "WEBHOOK_EVENT",           # (hub, event: WebhookEvent)
]

REQUIRED_SCOPES = ["orders:read", "orders:write", "products:read", "products:write", "stock:read",
                   "stock:write"]

STATE_TTL = timedelta(days=14)


class PluginData:
    def __init__(self, uuid: str, name: str, version: str, description: str, credits: str, path: str,
                 module: Any, enabled: bool):
        self.uuid = uuid
        self.name = name
        self.version = version
        self.description = description
        self.credits = credits
        self.path = path
        self.module = module
        self.enabled = enabled
        self.commands: dict[str, str] = {}


class IziMarketHub:
    def __init__(self, main_cfg, ad_cfg):
        self.MAIN_CFG = main_cfg
        self.AD_CFG = ad_cfg
        im = main_cfg["IziMarket"]
        self.client = Client(im["apiKey"], locale=im["locale"], proxy=im["proxy"] or None)
        self.store = JSONStore()
        self.goods = GoodsStorage()
        self.tg: TGBot | None = None

        self.me: dict = {}
        self.running = False
        self.start_time = time.time()

        self.handlers: dict[str, list[Callable]] = {e: [] for e in EVENTS}
        self.plugins: dict[str, PluginData] = {}

        self._orders_lock = threading.RLock()
        self._wake_orders = threading.Event()
        self._wake_refill = threading.Event()
        self._products_cache: dict[str, tuple[float, Product]] = {}
        self._title_map: tuple[float, dict[str, str]] = (0, {})

    # ------------------------------------------------------------------ настройки

    def setting(self, key: str) -> bool:
        return self.MAIN_CFG.getboolean("IziMarket", key)

    def toggle_setting(self, section: str, key: str) -> bool:
        new = "0" if self.MAIN_CFG.getboolean(section, key) else "1"
        self.MAIN_CFG.set(section, key, new)
        self.save_main_config()
        return new == "1"

    def save_main_config(self) -> None:
        cfg_loader.save_config(self.MAIN_CFG, cfg_loader.MAIN_CFG)

    def save_ad_config(self) -> None:
        cfg_loader.save_config(self.AD_CFG, cfg_loader.AD_CFG)

    # ------------------------------------------------------------------ события

    def add_handler(self, event: str, fn: Callable, plugin_uuid: str | None = None) -> None:
        if event not in self.handlers:
            raise ValueError(f"Неизвестное событие {event}")
        fn.plugin_uuid = plugin_uuid
        self.handlers[event].append(fn)

    def dispatch(self, event: str, *args) -> None:
        for fn in list(self.handlers[event]):
            uuid = getattr(fn, "plugin_uuid", None)
            if uuid and (uuid not in self.plugins or not self.plugins[uuid].enabled):
                continue
            try:
                fn(self, *args)
            except Exception:
                logger.error(f"Ошибка в обработчике {event} ({getattr(fn, '__module__', '?')}."
                             f"{getattr(fn, '__name__', '?')}):\n{traceback.format_exc()}")

    # ------------------------------------------------------------------ плагины

    def load_plugins(self, directory: str = "plugins") -> None:
        os.makedirs(directory, exist_ok=True)
        disabled = set(self.store.get("disabled_plugins", []))
        for fname in sorted(os.listdir(directory)):
            if not fname.endswith(".py") or fname.startswith("_"):
                continue
            path = os.path.join(directory, fname)
            try:
                self._load_plugin(path, disabled)
            except Exception:
                logger.error(f"Плагин {fname} не загружен:\n{traceback.format_exc()}")

    def _load_plugin(self, path: str, disabled: set[str]) -> PluginData:
        name = "imh_plugin_" + os.path.splitext(os.path.basename(path))[0]
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        for attr in ("NAME", "VERSION", "DESCRIPTION", "CREDITS", "UUID"):
            if not hasattr(module, attr):
                raise ValueError(f"нет обязательного поля {attr}")
        if module.UUID in self.plugins:
            raise ValueError(f"UUID {module.UUID} уже занят плагином {self.plugins[module.UUID].name}")
        data = PluginData(module.UUID, module.NAME, module.VERSION, module.DESCRIPTION, module.CREDITS, path,
                          module, module.UUID not in disabled)
        self.plugins[module.UUID] = data
        for event in EVENTS:
            for fn in getattr(module, f"BIND_TO_{event}", []) or []:
                self.add_handler(event, fn, module.UUID)
        logger.info(f"Плагин {data.name} v{data.version} загружен{'' if data.enabled else ' (выключен)'}")
        return data

    def toggle_plugin(self, uuid: str) -> bool:
        p = self.plugins[uuid]
        p.enabled = not p.enabled
        self.store.update("disabled_plugins",
                          lambda old: sorted((set(old or []) - {uuid}) | (set() if p.enabled else {uuid})))
        return p.enabled

    # ------------------------------------------------------------------ товары

    def get_product(self, product_id: str, max_age: float = 60) -> Product:
        cached = self._products_cache.get(product_id)
        if cached and time.time() - cached[0] < max_age:
            return cached[1]
        p = self.client.get_product(product_id)
        self._products_cache[product_id] = (time.time(), p)
        return p

    def forget_product(self, product_id: str) -> None:
        self._products_cache.pop(product_id, None)

    def title_to_id(self, title: str) -> str | None:
        ts, mapping = self._title_map
        if time.time() - ts > 600 or title not in mapping:
            mapping = {}
            for p in self.client.iter_products():
                mapping.setdefault(p.title, p.id)
                self._products_cache[p.id] = (time.time(), p)
            self._title_map = (time.time(), mapping)
        return mapping.get(title)

    def find_ad_section(self, product_id: str | None, title: str | None) -> str | None:
        """Секция автовыдачи: по id товара, иначе по точному названию."""
        if product_id and self.AD_CFG.has_section(product_id):
            return product_id
        if title and self.AD_CFG.has_section(title):
            return title
        return None

    def section_product_id(self, section: str) -> str | None:
        if _looks_like_uuid(section):
            return section
        try:
            return self.title_to_id(section)
        except IziAPIError as e:
            logger.warning(f"Не удалось найти товар «{section}»: {e}")
            return None

    def disable_product(self, product: Product, reason: str) -> None:
        if product.status not in ("active", "pending"):
            return
        try:
            new = self.client.unpublish_product(product.id)
        except IziAPIError as e:
            logger.error(f"Не удалось снять «{product.title}»: {e}")
            return
        self.forget_product(product.id)
        self.store.update("disabled_by_bot", lambda old: sorted(set(old or []) | {product.id}))
        logger.info(f"Товар «{product.title}» снят с продажи: {reason}")
        self.dispatch("PRODUCT_DISABLED", new, reason)

    def restore_product(self, product_id: str) -> None:
        if product_id not in (self.store.get("disabled_by_bot") or []):
            return
        try:
            new = self.client.publish_product(product_id)
        except IziAPIError as e:
            logger.error(f"Не удалось вернуть товар {product_id} в продажу: {e}")
            return
        self.forget_product(product_id)
        self.store.update("disabled_by_bot", lambda old: sorted(set(old or []) - {product_id}))
        logger.info(f"Товар «{new.title}» снова в продаже ({new.status_ru})")
        self.dispatch("PRODUCT_RESTORED", new)

    def check_restore(self) -> None:
        """Возвращает в продажу товары, снятые ботом, если в их файлах снова есть строки."""
        if not self.setting("autoRestore"):
            return
        for section in self.AD_CFG.sections():
            s = self.AD_CFG[section]
            if cfg_loader.is_true(s.get("disableAutoRestore")) or not s.get("productsFileName"):
                continue
            pid = self.section_product_id(section)
            if pid and pid in (self.store.get("disabled_by_bot") or []) and \
                    self.goods.count(s["productsFileName"]) > 0:
                self.restore_product(pid)

    # ------------------------------------------------------------------ сделки

    def mark_order(self, order: Order) -> None:
        stamp = order.updated_at.isoformat() if order.updated_at else _now().isoformat()
        self.store.update("orders", lambda old: {**(old or {}), order.id: [order.status, stamp]})

    def known_status(self, order_id: str) -> str | None:
        rec = (self.store.get("orders") or {}).get(order_id)
        return rec[0] if rec else None

    def process_order(self, order: Order) -> None:
        with self._orders_lock:
            old = self.known_status(order.id)
            if old == order.status:
                return
            self.mark_order(order)
        if old is None:
            logger.info(f"Новая сделка #{order.id[:8]}: «{order.product_title}» x{order.quantity}, "
                        f"{order.amount}, покупатель {order.buyer.username} ({order.status_ru})")
            self.dispatch("NEW_ORDER", order)
        else:
            logger.info(f"Сделка #{order.id[:8]}: {old} → {order.status}")
            self.dispatch("ORDER_STATUS_CHANGED", order, old)

    def deliver(self, order: Order, content: str | None, fields: dict | None = None,
                by_bot: bool = False) -> Order:
        """Выдать сделку. Бросает IziAPIError/NetworkError — решать вызывающему."""
        new = self.client.deliver_order(order.id, content, fields)
        with self._orders_lock:
            self.mark_order(new)
        logger.info(f"Сделка #{order.id[:8]} выдана{' автоматически' if by_bot else ''}")
        self.dispatch("ORDER_DELIVERED", new, content or "", by_bot)
        return new

    def poll_orders(self) -> int:
        """Опрос «хотя бы один раз»: с наибольшего updated_at минус минута, повторы — по статусу."""
        raw = self.store.get("orders_cursor")
        cursor = datetime.fromisoformat(raw) if raw else _now().replace(microsecond=0)
        if not raw:
            self.store.set("orders_cursor", cursor.isoformat())
        since = (cursor - timedelta(minutes=1)).isoformat()
        newest = cursor
        n = 0
        for order in self.client.iter_orders(updated_since=since):
            n += 1
            self.process_order(order)
            if order.updated_at and order.updated_at > newest:
                newest = order.updated_at
        if newest != cursor:
            self.store.set("orders_cursor", newest.isoformat())
        return n

    def process_pending_on_start(self) -> None:
        """Сделки, оплаченные пока бот был выключен."""
        count = 0
        for order in self.client.iter_orders(status="paid"):
            if self.known_status(order.id) is None:
                count += 1
                self.process_order(order)
        if count:
            logger.info(f"Обработано ожидающих выдачи сделок: {count}")

    def prune_state(self) -> None:
        limit = _now() - STATE_TTL
        self.store.update("orders", lambda old: {k: v for k, v in (old or {}).items()
                                                 if v[0] in ("paid", "disputed")
                                                 or datetime.fromisoformat(v[1]) >= limit})

    def wake(self, orders: bool = False, refill: bool = False) -> None:
        if orders:
            self._wake_orders.set()
        if refill:
            self._wake_refill.set()

    # ------------------------------------------------------------------ потоки

    def _orders_loop(self) -> None:
        interval = self.MAIN_CFG.getint("IziMarket", "pollInterval")
        last_prune = 0.0
        while self.running:
            try:
                self.poll_orders()
                if time.time() - last_prune > 3600:
                    self.prune_state()
                    last_prune = time.time()
            except InvalidKeyError as e:
                logger.critical(f"Ключ API больше не действует ({e.code}). Выпустите новый ключ и перезапустите.")
                if self.tg:
                    self.tg.notify_system("🔑 Ключ API больше не действует. Выпустите новый ключ в кабинете "
                                          "и обновите configs/_main.cfg.")
                self.running = False
                return
            except (IziAPIError, NetworkError) as e:
                logger.warning(f"Опрос сделок: {e}")
                interval_err = getattr(e, "retry_after", None) or interval
                self._wake_orders.wait(max(interval, interval_err))
                self._wake_orders.clear()
                continue
            except Exception:
                logger.error(f"Опрос сделок упал:\n{traceback.format_exc()}")
            self._wake_orders.wait(interval)
            self._wake_orders.clear()

    def _refill_loop(self) -> None:
        from handlers import refill_stock_all  # здесь, чтобы не было циклического импорта
        interval = self.MAIN_CFG.getint("StockRefill", "checkInterval")
        while self.running:
            try:
                if self.setting("stockRefill"):
                    refill_stock_all(self)
                self.check_restore()
            except Exception:
                logger.error(f"Пополнение склада упало:\n{traceback.format_exc()}")
            self._wake_refill.wait(interval)
            self._wake_refill.clear()

    # ------------------------------------------------------------------ жизненный цикл

    def init(self) -> None:
        self.dispatch("PRE_INIT")
        try:
            self.me = self.client.get_me()
        except InvalidKeyError:
            raise SystemExit("Ключ API не действует: выпустите новый в кабинете IziMarket → Настройки → API")
        key = self.me.get("key", {})
        logger.info(f"Аккаунт: {self.me.get('username')}  ключ {key.get('prefix')}… до {key.get('expires_at')}")
        missing = [s for s in REQUIRED_SCOPES if s not in key.get("scopes", [])]
        if missing:
            logger.warning(f"У ключа нет прав: {', '.join(missing)} — часть функций работать не будет")
        exp = key.get("expires_at")
        if exp and datetime.fromisoformat(exp) - _now() < timedelta(days=7):
            logger.warning(f"Ключ API истекает {exp} — выпустите новый заранее")
        self.dispatch("POST_INIT")

    def run(self) -> None:
        self.dispatch("PRE_START")
        self.running = True
        if self.setting("deliverPendingOnStart"):
            try:
                self.process_pending_on_start()
            except (IziAPIError, NetworkError) as e:
                logger.warning(f"Не удалось получить ожидающие сделки: {e}")
        threads = [threading.Thread(target=self._orders_loop, name="orders", daemon=True),
                   threading.Thread(target=self._refill_loop, name="refill", daemon=True)]
        for t in threads:
            t.start()
        logger.info(f"IziMarketHub v{VERSION} запущен. Автор: {AUTHOR} ({AUTHOR_LINK})")
        self.dispatch("POST_START")
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Остановка…")
        finally:
            self.stop()

    def stop(self) -> None:
        if not self.running:
            return
        self.dispatch("PRE_STOP")
        self.running = False
        self._wake_orders.set()
        self._wake_refill.set()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _looks_like_uuid(s: str) -> bool:
    import uuid
    try:
        uuid.UUID(s)
        return True
    except ValueError:
        return False
