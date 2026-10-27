"""Telegram-бот управления IziMarketHub."""

from __future__ import annotations

import logging
import os
import threading
import time
import traceback
from datetime import date, timedelta
from html import escape
from typing import TYPE_CHECKING, Callable

import telebot
from telebot import apihelper
from telebot.types import (BotCommand, CallbackQuery, InlineKeyboardButton as Btn, InlineKeyboardMarkup, Message)

from IziAPI import Order, Product
from IziAPI.exceptions import IziAPIError, NetworkError
from Utils.config_loader import AD_SCHEMA, is_true
from Utils.logger import LOG_FILE
from . import utils as u

if TYPE_CHECKING:
    from hub import IziMarketHub

logger = logging.getLogger("IMH.tg")

NOTIFY_KINDS = {
    "new_order": "🛒 Новые сделки",
    "delivery": "📬 Выдача",
    "status": "🔄 Смена статуса",
    "stock": "📦 Склад и товары",
    "system": "⚙️ Системные",
}

GLOBAL_SWITCHES = {
    "autoDelivery": "Автовыдача",
    "autoDisable": "Автодеактивация",
    "autoRestore": "Автовосстановление",
    "stockRefill": "Пополнение склада",
    "syncQuantity": "Синхр. количества",
}

MAX_LOGIN_ATTEMPTS = 5
LOGIN_BLOCK_SECONDS = 600

DEFAULT_RESPONSE = "Спасибо за покупку, $username!\\nВаш товар:\\n$product"


def _onoff(v: bool) -> str:
    return "🟢" if v else "🔴"


class TGBot:
    def __init__(self, hub: IziMarketHub):
        self.hub = hub
        tg = hub.MAIN_CFG["Telegram"]
        if tg["proxy"]:
            apihelper.proxy = {"https": tg["proxy"], "http": tg["proxy"]}
        self.bot = telebot.TeleBot(tg["token"], parse_mode="HTML", threaded=True)
        self._pending: dict[int, tuple[str, str]] = {}  # chat_id → (действие, аргумент)
        self._attempts: dict[int, tuple[int, float]] = {}
        self._register()

    # ------------------------------------------------------------------ доступ

    @property
    def chats(self) -> dict[str, dict]:
        return self.hub.store.get("tg_chats") or {}

    def authorized(self, chat_id: int) -> bool:
        return str(chat_id) in self.chats

    def _authorize(self, chat_id: int) -> None:
        self.hub.store.update("tg_chats", lambda old: {**(old or {}),
                                                        str(chat_id): {k: True for k in NOTIFY_KINDS}})

    def _guard(self, fn: Callable) -> Callable:
        def wrapper(obj):
            chat_id = obj.message.chat.id if isinstance(obj, CallbackQuery) else obj.chat.id
            if not self.authorized(chat_id):
                if isinstance(obj, CallbackQuery):
                    self.bot.answer_callback_query(obj.id, "Нет доступа")
                return
            try:
                fn(obj)
            except (IziAPIError, NetworkError) as e:
                self.bot.send_message(chat_id, f"❌ Ошибка API: {escape(str(e))}")
            except Exception:
                logger.error(traceback.format_exc())
                self.bot.send_message(chat_id, "❌ Внутренняя ошибка, подробности в логе")
        wrapper.__name__ = fn.__name__
        return wrapper

    # ------------------------------------------------------------------ уведомления

    def send(self, chat_id: int | str, text: str, markup=None) -> None:
        try:
            self.bot.send_message(chat_id, u.truncate(text), reply_markup=markup, disable_web_page_preview=True)
        except Exception as e:
            logger.warning(f"Не удалось отправить сообщение в {chat_id}: {e}")

    def notify(self, kind: str, text: str, markup=None) -> None:
        for chat_id, prefs in self.chats.items():
            if prefs.get(kind, True):
                self.send(chat_id, text, markup)

    def notify_system(self, text: str) -> None:
        self.notify("system", text)

    def _order_markup(self, order: Order) -> InlineKeyboardMarkup:
        kb = InlineKeyboardMarkup()
        if order.status == "paid":
            kb.add(Btn("✍️ Выдать вручную", callback_data=f"deliver:{order.id}"))
        if order.product_id:
            kb.add(Btn("🔗 Товар на сайте", url=f"https://izi.market/products/{order.product_id}"))
        return kb

    # события ядра
    def on_new_order(self, hub, order: Order) -> None:
        self.notify("new_order", u.order_text(order), self._order_markup(order))

    def on_status(self, hub, order: Order, old: str) -> None:
        icon = {"disputed": "⚠️", "completed": "✅", "refunded": "↩️", "cancelled": "🚫"}.get(order.status, "🔄")
        self.notify("status", f"{icon} Сделка {u.code('#' + order.id[:8])} «{escape(order.product_title or '')}»: "
                              f"{escape(old)} → {u.b(order.status_ru)}")

    def on_delivered(self, hub, order: Order, content: str, by_bot: bool) -> None:
        who = "автоматически" if by_bot else "вручную"
        self.notify("delivery", f"📬 Сделка {u.code('#' + order.id[:8])} выдана {who}\n"
                                f"«{escape(order.product_title or '')}» → {u.b(order.buyer.username or '—')}")

    def on_delivery_failed(self, hub, order: Order, reason: str) -> None:
        self.notify("delivery", f"❗ Автовыдача сделки {u.code('#' + order.id[:8])} не удалась\n"
                                f"«{escape(order.product_title or '')}»: {escape(reason)}",
                    self._order_markup(order))

    def on_product_disabled(self, hub, product: Product, reason: str) -> None:
        self.notify("stock", f"⏸ Товар «{escape(product.title)}» снят с продажи: {escape(reason)}")

    def on_product_restored(self, hub, product: Product) -> None:
        self.notify("stock", f"▶️ Товар «{escape(product.title)}» снова выставлен ({escape(product.status_ru)})")

    def on_stock_refilled(self, hub, product: Product, added: int) -> None:
        self.notify("stock", f"📦 Склад «{escape(product.title)}» пополнен на {added}")

    def on_webhook(self, hub, event) -> None:
        if event.type == "product.moderation.rejected":
            p = event.data.get("product") or {}
            self.notify("stock", f"🚫 Модерация отклонила «{escape(p.get('title', ''))}»")
        elif event.type == "product.needs_update":
            p = event.data.get("product") or {}
            self.notify("stock", f"✏️ Товар «{escape(p.get('title', ''))}» нужно обновить")

    def bind(self) -> None:
        h = self.hub.add_handler
        h("NEW_ORDER", self.on_new_order)
        h("ORDER_STATUS_CHANGED", self.on_status)
        h("ORDER_DELIVERED", self.on_delivered)
        h("DELIVERY_FAILED", self.on_delivery_failed)
        h("PRODUCT_DISABLED", self.on_product_disabled)
        h("PRODUCT_RESTORED", self.on_product_restored)
        h("STOCK_REFILLED", self.on_stock_refilled)
        h("WEBHOOK_EVENT", self.on_webhook)

    # ------------------------------------------------------------------ меню

    def main_menu(self) -> InlineKeyboardMarkup:
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(Btn("⚙️ Переключатели", callback_data="sw"), Btn("🔔 Уведомления", callback_data="nt"))
        kb.add(Btn("📦 Автовыдача", callback_data="ad:0"), Btn("📁 Файлы товаров", callback_data="gf"))
        kb.add(Btn("🧾 Сделки", callback_data="orders"), Btn("🛍 Мои товары", callback_data="pr:1"))
        kb.add(Btn("💰 Баланс", callback_data="balance"), Btn("📊 Статистика", callback_data="stats"))
        kb.add(Btn("🧩 Плагины", callback_data="pl"), Btn("ℹ️ О боте", callback_data="about"))
        return kb

    def _back(self, kb: InlineKeyboardMarkup | None = None, to: str = "menu") -> InlineKeyboardMarkup:
        kb = kb or InlineKeyboardMarkup()
        kb.add(Btn("◀️ Назад", callback_data=to))
        return kb

    def _edit(self, call: CallbackQuery, text: str, kb: InlineKeyboardMarkup | None = None) -> None:
        try:
            self.bot.edit_message_text(u.truncate(text), call.message.chat.id, call.message.message_id,
                                       reply_markup=kb, disable_web_page_preview=True)
        except apihelper.ApiTelegramException as e:
            if "message is not modified" not in str(e):
                raise
        self.bot.answer_callback_query(call.id)

    def switches_view(self) -> tuple[str, InlineKeyboardMarkup]:
        kb = InlineKeyboardMarkup()
        for key, title in GLOBAL_SWITCHES.items():
            kb.add(Btn(f"{_onoff(self.hub.setting(key))} {title}", callback_data=f"swt:{key}"))
        return "⚙️ <b>Глобальные переключатели</b>", self._back(kb)

    def notify_view(self, chat_id: int) -> tuple[str, InlineKeyboardMarkup]:
        prefs = self.chats.get(str(chat_id), {})
        kb = InlineKeyboardMarkup()
        for key, title in NOTIFY_KINDS.items():
            kb.add(Btn(f"{_onoff(prefs.get(key, True))} {title}", callback_data=f"ntt:{key}"))
        return "🔔 <b>Уведомления в этот чат</b>", self._back(kb)

    def ad_view(self, page: int) -> tuple[str, InlineKeyboardMarkup]:
        sections = self.hub.AD_CFG.sections()
        per = 8
        kb = InlineKeyboardMarkup()
        for i, sec in enumerate(sections[page * per:(page + 1) * per], start=page * per):
            s = self.hub.AD_CFG[sec]
            f = s.get("productsFileName")
            cnt = f" [{self.hub.goods.count(f)}]" if f else ""
            kb.add(Btn(f"{_onoff(not is_true(s.get('disable')))} {sec[:40]}{cnt}", callback_data=f"ade:{i}"))
        nav = []
        if page > 0:
            nav.append(Btn("⬅️", callback_data=f"ad:{page - 1}"))
        if (page + 1) * per < len(sections):
            nav.append(Btn("➡️", callback_data=f"ad:{page + 1}"))
        if nav:
            kb.row(*nav)
        kb.add(Btn("➕ Привязать товар", callback_data="adb:1"))
        text = (f"📦 <b>Автовыдача</b> — {len(sections)} товаров\n"
                f"Глобально: {_onoff(self.hub.setting('autoDelivery'))}\n"
                "В скобках — сколько строк осталось в файле.")
        return text, self._back(kb)

    def ad_edit_view(self, idx: int) -> tuple[str, InlineKeyboardMarkup]:
        sec = self.hub.AD_CFG.sections()[idx]
        s = self.hub.AD_CFG[sec]
        f = s.get("productsFileName")
        text = (f"📦 <b>{escape(sec)}</b>\n\n"
                f"Текст выдачи:\n<code>{escape(s.get('response') or '$product')}</code>\n\n"
                f"Файл: {u.code(f) if f else '—'}" + (f" ({self.hub.goods.count(f)} строк)" if f else "") +
                (f"\nПоля выдачи: {u.code(s.get('fields'))}" if s.get("fields") else ""))
        kb = InlineKeyboardMarkup(row_width=1)
        for key, title in (("disable", "Автовыдача"), ("disableAutoDisable", "Автодеактивация"),
                           ("disableAutoRestore", "Автовосстановление")):
            kb.add(Btn(f"{_onoff(not is_true(s.get(key)))} {title}", callback_data=f"adt:{idx}:{key}"))
        kb.add(Btn(f"{_onoff(is_true(s.get('stockRefill')))} Пополнять склад площадки",
                   callback_data=f"adt:{idx}:stockRefill"))
        kb.add(Btn("✏️ Изменить текст", callback_data=f"adr:{idx}"))
        if f:
            kb.add(Btn("➕ Добавить товар в файл", callback_data=f"gadd:{f}"))
        kb.add(Btn("🗑 Отвязать", callback_data=f"add:{idx}"))
        return text, self._back(kb, "ad:0")

    def goods_view(self) -> tuple[str, InlineKeyboardMarkup]:
        kb = InlineKeyboardMarkup()
        for f in self.hub.goods.files()[:40]:
            kb.add(Btn(f"{f} [{self.hub.goods.count(f)}]", callback_data=f"gfo:{f}"[:64]))
        return "📁 <b>Файлы товаров</b> (storage/products)", self._back(kb)

    def goods_file_view(self, f: str) -> tuple[str, InlineKeyboardMarkup]:
        preview = self.hub.goods.peek(f, 5)
        text = (f"📁 {u.code(f)} — {self.hub.goods.count(f)} строк\n\nПервые строки:\n" +
                ("\n".join(u.code(x[:80]) for x in preview) or "— пусто —"))
        kb = InlineKeyboardMarkup()
        kb.add(Btn("➕ Добавить", callback_data=f"gadd:{f}"[:64]), Btn("📤 Скачать", callback_data=f"gget:{f}"[:64]))
        kb.add(Btn("🧹 Очистить", callback_data=f"gclr:{f}"[:64]))
        return text, self._back(kb, "gf")

    def products_view(self, page: int, bind: bool = False) -> tuple[str, InlineKeyboardMarkup]:
        items, has_next = self.hub.client.list_products(page=page)
        kb = InlineKeyboardMarkup()
        prefix = "adbp" if bind else "pro"
        for p in items[:40]:
            mark = "✅ " if self.hub.find_ad_section(p.id, p.title) else ""
            kb.add(Btn(f"{mark}{p.title[:45]} · {p.price}", callback_data=f"{prefix}:{p.id}"))
        nav = []
        if page > 1:
            nav.append(Btn("⬅️", callback_data=f"{'adb' if bind else 'pr'}:{page - 1}"))
        if has_next:
            nav.append(Btn("➡️", callback_data=f"{'adb' if bind else 'pr'}:{page + 1}"))
        if nav:
            kb.row(*nav)
        title = "Выберите товар для автовыдачи" if bind else "🛍 <b>Мои товары</b>"
        return f"{title} (стр. {page})", self._back(kb, "ad:0" if bind else "menu")

    def product_view(self, pid: str) -> tuple[str, InlineKeyboardMarkup]:
        p = self.hub.get_product(pid, max_age=0)
        text = (f"🛍 <b>{escape(p.title)}</b>\n{u.product_line(p)}\nПродаж: {p.sales}\n"
                f"{u.code(p.id)}")
        kb = InlineKeyboardMarkup(row_width=2)
        if p.status in ("active", "pending"):
            kb.add(Btn("⏸ Снять с продажи", callback_data=f"pun:{p.id}"))
        else:
            kb.add(Btn("▶️ Выставить", callback_data=f"ppub:{p.id}"))
        kb.add(Btn("💲 Цена", callback_data=f"pprice:{p.id}"),
               *([] if p.stock_managed else [Btn("🔢 Количество", callback_data=f"pqty:{p.id}")]))
        kb.add(Btn("🔗 На сайте", url=p.url))
        return text, self._back(kb, "pr:1")

    def plugins_view(self) -> tuple[str, InlineKeyboardMarkup]:
        kb = InlineKeyboardMarkup()
        for uuid, p in self.hub.plugins.items():
            kb.add(Btn(f"{_onoff(p.enabled)} {p.name} v{p.version}", callback_data=f"plt:{uuid}"[:64]))
        kb.add(Btn("➕ Добавить плагин", callback_data="pladd"))
        text = ("🧩 <b>Плагины</b>\n\n⚠️ Ставьте плагины только из проверенных источников: "
                "плагин получает полный доступ к компьютеру и ключу API.")
        return text, self._back(kb)

    def about_text(self) -> str:
        from hub import AUTHOR, AUTHOR_LINK, VERSION
        up = int(time.time() - self.hub.start_time)
        return (f"🤖 <b>IziMarketHub</b> v{VERSION}\n"
                f"Автор: <a href=\"{AUTHOR_LINK}\">{AUTHOR}</a>\n"
                f"Аккаунт: {u.b(self.hub.me.get('username', '?'))}\n"
                f"Работает: {up // 3600} ч {up % 3600 // 60} мин\n"
                f"Плагинов: {len(self.hub.plugins)}")

    # ------------------------------------------------------------------ данные

    def balance_text(self) -> str:
        bal = self.hub.client.get_balance()
        return (f"💰 <b>Баланс</b>\nВсего: {u.b(bal.balance)}\nДоступно: {u.b(bal.available)}\n"
                f"Забронировано: {escape(str(bal.held))}"
                + (f"\nТолько на покупки: {escape(str(bal.spend_only))}" if bal.spend_only else ""))

    def orders_text(self) -> str:
        items, _ = self.hub.client.list_orders(limit=10)
        if not items:
            return "🧾 Сделок пока нет"
        lines = ["🧾 <b>Последние сделки</b>"]
        for o in items:
            lines.append(f"{u.code('#' + o.id[:8])} {escape(o.status_ru)} · «{escape((o.product_title or '')[:30])}» "
                         f"×{o.quantity} · {escape(str(o.amount))} · {escape(o.buyer.username or '')}")
        paid, _ = self.hub.client.list_orders(status="paid", limit=50)
        lines.append(f"\nЖдут выдачи: {u.b(len(paid))}")
        return "\n".join(lines)

    def stats_text(self) -> str:
        to = date.today()
        a = self.hub.client.get_analytics(date_from=(to - timedelta(days=6)).isoformat(), date_to=to.isoformat(),
                                          sections="")
        lines = [f"📊 <b>За 7 дней</b> ({a['period']['from']} — {a['period']['to']})"]
        cur, prev = a.get("current", {}), a.get("previous", {})
        for k, v in cur.items():
            pv = prev.get(k)
            if isinstance(v, dict):
                val = f"{v['amount_minor'] / 100:,.2f} {v.get('currency', '')}".replace(",", " ")
                pval = f"{pv['amount_minor'] / 100:,.2f}".replace(",", " ") if isinstance(pv, dict) else "—"
            else:
                val, pval = str(v), str(pv) if pv is not None else "—"
            lines.append(f"• {escape(k)}: {u.b(val)} (было {escape(pval)})")
        return "\n".join(lines)

    # ------------------------------------------------------------------ обработчики

    def _register(self) -> None:
        bot = self.bot

        @bot.message_handler(commands=["start"])
        def start(m: Message):
            if self.authorized(m.chat.id):
                return bot.send_message(m.chat.id, "Вы уже авторизованы.", reply_markup=self.main_menu())
            bot.send_message(m.chat.id, "🔒 Это бот IziMarketHub. Отправьте пароль доступа.")

        bot.message_handler(commands=["menu"])(self._guard(
            lambda m: bot.send_message(m.chat.id, "📋 <b>Меню IziMarketHub</b>", reply_markup=self.main_menu())))
        bot.message_handler(commands=["balance"])(self._guard(lambda m: self.send(m.chat.id, self.balance_text())))
        bot.message_handler(commands=["orders"])(self._guard(lambda m: self.send(m.chat.id, self.orders_text())))
        bot.message_handler(commands=["stats"])(self._guard(lambda m: self.send(m.chat.id, self.stats_text())))
        bot.message_handler(commands=["about"])(self._guard(lambda m: self.send(m.chat.id, self.about_text())))

        @bot.message_handler(commands=["logs"])
        @self._guard
        def logs(m: Message):
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, "rb") as f:
                    bot.send_document(m.chat.id, f, visible_file_name="log.txt")

        @bot.message_handler(commands=["deliver"])
        @self._guard
        def deliver_cmd(m: Message):
            parts = m.text.split(maxsplit=2)
            if len(parts) < 2:
                return self.send(m.chat.id, "Использование: /deliver &lt;id сделки&gt; [текст выдачи]")
            if len(parts) == 3:
                return self._do_deliver(m.chat.id, parts[1], parts[2])
            self._ask(m.chat.id, "deliver", parts[1], "✍️ Отправьте текст выдачи для сделки")

        @bot.message_handler(commands=["cancel"])
        def cancel(m: Message):
            self._pending.pop(m.chat.id, None)
            bot.send_message(m.chat.id, "Отменено")

        @bot.message_handler(content_types=["document"])
        @self._guard
        def document(m: Message):
            action, arg = self._pending.pop(m.chat.id, (None, None))
            if action not in ("gadd", "pladd"):
                return self.send(m.chat.id, "Файл не ожидался. Откройте нужный пункт меню и нажмите «Добавить».")
            data = bot.download_file(bot.get_file(m.document.file_id).file_path)
            if action == "gadd":
                self._add_goods(m.chat.id, arg, data.decode("utf-8", "replace").splitlines())
            else:
                self._save_plugin(m.chat.id, m.document.file_name, data)

        @bot.message_handler(func=lambda m: True, content_types=["text"])
        def text(m: Message):
            if not self.authorized(m.chat.id):
                return self._try_login(m)
            if m.chat.id in self._pending:
                return self._guard(self._handle_pending)(m)
            bot.send_message(m.chat.id, "📋 <b>Меню IziMarketHub</b>", reply_markup=self.main_menu())

        @bot.callback_query_handler(func=lambda c: True)
        @self._guard
        def callback(c: CallbackQuery):
            self._callback(c)

    def _try_login(self, m: Message) -> None:
        count, since = self._attempts.get(m.chat.id, (0, 0))
        if count >= MAX_LOGIN_ATTEMPTS and time.time() - since < LOGIN_BLOCK_SECONDS:
            return
        if count >= MAX_LOGIN_ATTEMPTS:
            count = 0
        stored = self.hub.MAIN_CFG.get("Telegram", "secretKeyHash")
        if stored and u.check_password(m.text.strip(), stored):
            self._attempts.pop(m.chat.id, None)
            self._authorize(m.chat.id)
            try:
                self.bot.delete_message(m.chat.id, m.message_id)
            except Exception:
                pass
            logger.warning(f"В Telegram-боте авторизован чат {m.chat.id} (@{m.from_user.username})")
            self.bot.send_message(m.chat.id, "✅ Доступ открыт.", reply_markup=self.main_menu())
        else:
            self._attempts[m.chat.id] = (count + 1, time.time())
            logger.warning(f"Неверный пароль Telegram-бота от {m.chat.id} (@{m.from_user.username})")
            self.bot.send_message(m.chat.id, "❌ Неверный пароль")

    def _ask(self, chat_id: int, action: str, arg: str, prompt: str) -> None:
        self._pending[chat_id] = (action, arg)
        self.send(chat_id, prompt + "\n\n/cancel — отмена")

    def _handle_pending(self, m: Message) -> None:
        action, arg = self._pending.pop(m.chat.id)
        txt = m.text or ""
        if action == "deliver":
            self._do_deliver(m.chat.id, arg, txt)
        elif action == "gadd":
            self._add_goods(m.chat.id, arg, txt.splitlines())
        elif action == "adr":
            sec = self.hub.AD_CFG.sections()[int(arg)]
            self.hub.AD_CFG.set(sec, "response", txt.replace("\n", "\\n"))
            self.hub.save_ad_config()
            self.send(m.chat.id, "✅ Текст выдачи обновлён")
        elif action in ("pprice", "pqty"):
            try:
                value = float(txt.replace(",", ".").replace(" ", ""))
            except ValueError:
                return self.send(m.chat.id, "Нужно число")
            if action == "pprice":
                p = self.hub.client.set_product_price(arg, round(value * 100))
                self.send(m.chat.id, f"✅ Цена: {escape(str(p.price))} (статус: {escape(p.status_ru)})")
            else:
                p = self.hub.client.set_product_quantity(arg, int(value))
                self.send(m.chat.id, f"✅ Количество: {p.quantity}")
            self.hub.forget_product(arg)

    def _do_deliver(self, chat_id: int, order_id: str, content: str) -> None:
        order = self.hub.client.get_order(order_id)
        if order.status != "paid":
            return self.send(chat_id, f"Сделка уже в статусе «{escape(order.status_ru)}» — выдать нельзя")
        self.hub.deliver(order, content)
        self.send(chat_id, f"✅ Сделка {u.code('#' + order.id[:8])} выдана")

    def _add_goods(self, chat_id: int, file_name: str, lines: list[str]) -> None:
        n = self.hub.goods.add(file_name, lines)
        self.send(chat_id, f"✅ Добавлено {n} строк в {u.code(file_name)}, всего {self.hub.goods.count(file_name)}")
        self.hub.wake(refill=True)

    def _save_plugin(self, chat_id: int, name: str, data: bytes) -> None:
        name = os.path.basename(name or "")
        if not name.endswith(".py") or name.startswith("_"):
            return self.send(chat_id, "Плагин — это .py файл")
        path = os.path.join("plugins", name)
        with open(path, "wb") as f:
            f.write(data)
        logger.warning(f"Через Telegram установлен плагин {name}")
        self.send(chat_id, f"✅ Плагин {u.code(name)} сохранён. Перезапустите бота, чтобы он загрузился.")

    def _callback(self, c: CallbackQuery) -> None:
        chat_id = c.message.chat.id
        cmd, _, arg = c.data.partition(":")
        hub = self.hub

        if cmd == "menu":
            return self._edit(c, "📋 <b>Меню IziMarketHub</b>", self.main_menu())
        if cmd == "sw":
            return self._edit(c, *self.switches_view())
        if cmd == "swt":
            hub.toggle_setting("IziMarket", arg)
            return self._edit(c, *self.switches_view())
        if cmd == "nt":
            return self._edit(c, *self.notify_view(chat_id))
        if cmd == "ntt":
            hub.store.update("tg_chats", lambda old: {**old, str(chat_id): {
                **old[str(chat_id)], arg: not old[str(chat_id)].get(arg, True)}})
            return self._edit(c, *self.notify_view(chat_id))
        if cmd == "ad":
            return self._edit(c, *self.ad_view(int(arg)))
        if cmd == "ade":
            return self._edit(c, *self.ad_edit_view(int(arg)))
        if cmd == "adt":
            idx, key = arg.split(":")
            sec = hub.AD_CFG.sections()[int(idx)]
            hub.AD_CFG.set(sec, key, "0" if is_true(hub.AD_CFG.get(sec, key)) else "1")
            hub.save_ad_config()
            return self._edit(c, *self.ad_edit_view(int(idx)))
        if cmd == "adr":
            self.bot.answer_callback_query(c.id)
            return self._ask(chat_id, "adr", arg, "✏️ Отправьте новый текст выдачи. Переменные: $username, "
                                                  "$product, $product_title, $order_id, $quantity, $input_&lt;ключ&gt;")
        if cmd == "add":
            sec = hub.AD_CFG.sections()[int(arg)]
            hub.AD_CFG.remove_section(sec)
            hub.save_ad_config()
            return self._edit(c, *self.ad_view(0))
        if cmd == "adb":
            return self._edit(c, *self.products_view(int(arg), bind=True))
        if cmd == "adbp":
            p = hub.get_product(arg)
            if not hub.find_ad_section(p.id, p.title):
                hub.AD_CFG.add_section(p.id)
                for k, (default, _) in AD_SCHEMA.items():
                    hub.AD_CFG.set(p.id, k, default)
                hub.AD_CFG.set(p.id, "response", DEFAULT_RESPONSE)
                hub.AD_CFG.set(p.id, "productsFileName", f"{p.id[:8]}.txt")
                hub.save_ad_config()
                hub.goods.add(f"{p.id[:8]}.txt", [])
            idx = hub.AD_CFG.sections().index(hub.find_ad_section(p.id, p.title))
            return self._edit(c, *self.ad_edit_view(idx))
        if cmd == "gf":
            return self._edit(c, *self.goods_view())
        if cmd == "gfo":
            return self._edit(c, *self.goods_file_view(arg))
        if cmd == "gadd":
            self.bot.answer_callback_query(c.id)
            return self._ask(chat_id, "gadd", arg, f"➕ Отправьте строки товара для {u.code(arg)} — по одной на "
                                                   "строку, или .txt файлом. Перенос внутри товара — \\n")
        if cmd == "gget":
            self.bot.answer_callback_query(c.id)
            path = hub.goods.path(arg)
            if os.path.exists(path):
                with open(path, "rb") as f:
                    self.bot.send_document(chat_id, f, visible_file_name=arg)
            return
        if cmd == "gclr":
            kb = InlineKeyboardMarkup().add(Btn("Да, очистить", callback_data=f"gclry:{arg}"[:64]),
                                            Btn("Отмена", callback_data=f"gfo:{arg}"[:64]))
            return self._edit(c, f"Очистить {u.code(arg)}? Строки удалятся безвозвратно.", kb)
        if cmd == "gclry":
            hub.goods.clear(arg)
            return self._edit(c, *self.goods_file_view(arg))
        if cmd == "pr":
            return self._edit(c, *self.products_view(int(arg)))
        if cmd == "pro":
            return self._edit(c, *self.product_view(arg))
        if cmd in ("pun", "ppub"):
            p = hub.client.unpublish_product(arg) if cmd == "pun" else hub.client.publish_product(arg)
            hub.forget_product(arg)
            if cmd == "ppub":
                hub.store.update("disabled_by_bot", lambda old: sorted(set(old or []) - {arg}))
            return self._edit(c, *self.product_view(p.id))
        if cmd in ("pprice", "pqty"):
            self.bot.answer_callback_query(c.id)
            prompt = "💲 Новая цена в рублях (её называет продавец, без комиссии)" if cmd == "pprice" \
                else "🔢 Новое количество"
            return self._ask(chat_id, cmd, arg, prompt)
        if cmd == "deliver":
            self.bot.answer_callback_query(c.id)
            return self._ask(chat_id, "deliver", arg, f"✍️ Отправьте текст выдачи для сделки {u.code('#' + arg[:8])}")
        if cmd == "orders":
            return self._edit(c, self.orders_text(), self._back())
        if cmd == "balance":
            return self._edit(c, self.balance_text(), self._back())
        if cmd == "stats":
            return self._edit(c, self.stats_text(), self._back())
        if cmd == "pl":
            return self._edit(c, *self.plugins_view())
        if cmd == "plt":
            uuid = next((k for k in hub.plugins if k.startswith(arg)), None)
            if uuid:
                hub.toggle_plugin(uuid)
            return self._edit(c, *self.plugins_view())
        if cmd == "pladd":
            self.bot.answer_callback_query(c.id)
            return self._ask(chat_id, "pladd", "", "🧩 Отправьте .py файл плагина")
        if cmd == "about":
            return self._edit(c, self.about_text(), self._back())
        self.bot.answer_callback_query(c.id, "Неизвестная кнопка")

    # ------------------------------------------------------------------ запуск

    def start(self) -> None:
        try:
            self.bot.set_my_commands([
                BotCommand("menu", "Меню"), BotCommand("orders", "Последние сделки"),
                BotCommand("balance", "Баланс"), BotCommand("stats", "Статистика за 7 дней"),
                BotCommand("deliver", "Выдать сделку вручную"), BotCommand("logs", "Файл логов"),
                BotCommand("about", "О боте"), BotCommand("cancel", "Отменить ввод"),
            ])
            me = self.bot.get_me()
        except Exception as e:
            logger.error(f"Telegram-бот не запущен: {e}")
            return
        logger.info(f"Telegram-бот @{me.username} запущен")
        threading.Thread(target=self.bot.infinity_polling, kwargs={"timeout": 30, "long_polling_timeout": 30},
                         name="telegram", daemon=True).start()
        if not self.chats:
            logger.warning(f"Напишите боту @{me.username} и отправьте пароль, чтобы получать уведомления")
        self.notify_system("✅ IziMarketHub запущен")
