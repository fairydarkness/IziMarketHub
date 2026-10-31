"""Telegram-бот управления IziMarketHub."""

from __future__ import annotations

import logging
import os
import threading
import time
import traceback
from collections import OrderedDict
from datetime import date, timedelta
from html import escape
from typing import TYPE_CHECKING, Callable

import telebot
from telebot import apihelper
from telebot.types import (BotCommand, CallbackQuery, InlineKeyboardButton as Btn, InlineKeyboardMarkup, Message)

from IziAPI import Chat, ChatMessage, Money, Order, Product
from IziAPI.exceptions import IziAPIError, NetworkError
from Utils.config_loader import AD_SCHEMA, AR_SCHEMA, is_true
from Utils.templates import format_chat_text
from Utils import updater
from Utils.logger import LOG_FILE
from . import utils as u

if TYPE_CHECKING:
    from hub import IziMarketHub

logger = logging.getLogger("IMH.tg")

NOTIFY_KINDS = {
    "message": "💬 Сообщения в чатах",
    "command": "🤖 Команды автоответчика",
    "new_order": "🛒 Новые сделки",
    "delivery": "📬 Выдача",
    "status": "🔄 Смена статуса",
    "payout": "💸 Выход из холда",
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

# страницы главного меню: (подпись, callback)
MENU_PAGES = [
    [("💬 Чаты", "chl:0"), ("🧾 Сделки", "orders"),
     ("🛍 Мои товары", "pr:1"), ("📦 Автовыдача", "ad:0"),
     ("📁 Файлы товаров", "gf"), ("💰 Баланс", "balance")],
    [("🤖 Автоответчик", "ar:0"), ("📝 Заготовки ответов", "tpl"),
     ("👋 Сообщения бота", "chs"), ("🚫 Чёрный список", "bl"),
     ("📊 Статистика", "stats"), ("⚙️ Переключатели", "sw")],
    [("🔔 Уведомления", "nt"), ("🧩 Плагины", "pl"),
     ("📂 Конфиги", "cfg"), ("🔄 Обновление", "upd"),
     ("ℹ️ О боте", "about")],
]

# переключатели и тексты сообщений, которые бот сам пишет в чаты: [Chat] в _main.cfg
CHAT_SWITCHES = {
    "autoResponse": "Автоответчик",
    "greetings": "Приветствие новых собеседников",
    "greetingsNewOnly": "…только тем, кто пишет впервые",
    "greetingsOrderChats": "…и в чатах заказов",
    "newOrderReply": "Сообщение при новом заказе",
    "orderConfirmReply": "Сообщение при подтверждении",
    "markReadAfterResponse": "Читать чат после автоответа",
    "notifyOwnMessages": "Уведомлять о своих сообщениях",
}
CHAT_TEXTS = {
    "greetingsText": "👋 Приветствие",
    "newOrderReplyText": "🛒 Новый заказ",
    "orderConfirmReplyText": "✅ Подтверждение",
}
BLACKLIST_SWITCHES = {
    "blockDelivery": "Не выдавать автоматически",
    "blockResponse": "Не отвечать автоматически",
    "blockNotifications": "Не присылать уведомления",
}
CHAT_VARS = ("$username, $order_title, $order_id, $order_link, $message_text, $date, $time, $full_date. "
             "Переменная, которой нет (заказ в личном чате), будет пустой. "
             "$sleep=2 — пауза и новое сообщение, $photo=имя.png — картинка из storage/images")
ORDER_VARS = ("$username, $product_title, $order_id, $order_link, $quantity, $amount, $date, $time, $full_date. "
              "$sleep=2 — пауза и новое сообщение, $photo=имя.png — картинка из storage/images")
# что можно скачать и загрузить в «📂 Конфиги»: ключ → (файл, загрузчик-проверка, атрибут ядра)
CONFIG_FILES = {
    "ad": ("auto_delivery.cfg", "load_auto_delivery_config", "AD_CFG"),
    "ar": ("auto_response.cfg", "load_auto_response_config", "AR_CFG"),
}
# «Назад» из раздела возвращает на ту страницу меню, где он лежит
MENU_PAGE_OF = {cb.split(":")[0]: i for i, page in enumerate(MENU_PAGES) for _, cb in page}


def _onoff(v: bool) -> str:
    return "🟢" if v else "🔴"


# показатели-доли API отдаёт в процентах (dispute_rate = 100 → 100%)
PERCENT_METRICS = {"dispute_rate", "refund_rate", "conversion", "margin", "cost_coverage"}


def _num(v) -> str:
    return f"{v:.2f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v)


def _fmt_metric(v, key: str = "") -> str:
    """Показатель аналитики любой формы: деньги, число, процент или объект вроде рейтинга."""
    if v is None:
        return "—"
    if isinstance(v, dict):
        if "amount_minor" in v:
            return str(Money.from_dict(v))
        if "average" in v:  # рейтинг: {"average": 5, "reviews_count": 1}
            if v["average"] is None:
                return "—"
            count = v.get("reviews_count", v.get("count"))
            return f"{_num(v['average'])}" + (f" ({count} отз.)" if count is not None else "")
        for k in ("value", "percent", "rate", "count", "total"):
            if k in v and not isinstance(v[k], (dict, list)):
                return _fmt_metric(v[k], key)
        return ", ".join(f"{k}: {_fmt_metric(x)}" for k, x in v.items()) or "—"
    if isinstance(v, (int, float)) and key in PERCENT_METRICS:
        return f"{_num(v)}%"
    return _num(v)


class TGBot:
    def __init__(self, hub: IziMarketHub):
        self.hub = hub
        tg = hub.MAIN_CFG["Telegram"]
        if tg["proxy"]:
            apihelper.proxy = {"https": tg["proxy"], "http": tg["proxy"]}
        self.bot = telebot.TeleBot(tg["token"], parse_mode="HTML", threaded=True)
        self._pending: dict[int, tuple[str, str]] = {}  # chat_id → (действие, аргумент)
        self._attempts: dict[int, tuple[int, float]] = {}
        # (чат Telegram, id сообщения) → (чат IziMarket, это уведомление): ответ на него уходит собеседнику
        self._reply_map: OrderedDict[tuple[int, int], tuple[str, bool]] = OrderedDict()
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
            except updater.UpdateError as e:
                self.bot.send_message(chat_id, f"❌ Обновление не удалось:\n<pre>{escape(str(e))[:3500]}</pre>")
            except Exception:
                logger.error(traceback.format_exc())
                self.bot.send_message(chat_id, "❌ Внутренняя ошибка, подробности в логе")
        wrapper.__name__ = fn.__name__
        return wrapper

    # ------------------------------------------------------------------ уведомления

    def send(self, chat_id: int | str, text: str, markup=None) -> Message | None:
        try:
            return self.bot.send_message(chat_id, u.truncate(text), reply_markup=markup,
                                         disable_web_page_preview=True)
        except Exception as e:
            logger.warning(f"Не удалось отправить сообщение в {chat_id}: {e}")
            return None

    def notify(self, kind: str, text: str, markup=None, izi_chat: str | None = None) -> None:
        for chat_id, prefs in self.chats.items():
            if prefs.get(kind, True):
                msg = self.send(chat_id, text, markup)
                if msg and izi_chat:
                    self._remember_reply(msg, izi_chat, notification=True)

    def _remember_reply(self, msg: Message | CallbackQuery, izi_chat: str, notification: bool = False) -> None:
        if isinstance(msg, CallbackQuery):
            msg = msg.message
        key = (msg.chat.id, msg.message_id)
        self._reply_map[key] = (izi_chat, notification)
        while len(self._reply_map) > 3000:
            self._reply_map.popitem(last=False)

    def notify_system(self, text: str) -> None:
        self.notify("system", text)

    def _order_markup(self, order: Order) -> InlineKeyboardMarkup:
        kb = InlineKeyboardMarkup()
        if order.status == "paid":
            kb.add(Btn("✍️ Выдать вручную", callback_data=f"deliver:{order.id}"))
        if self.hub.chats_available:
            kb.add(Btn("✉️ Написать покупателю", callback_data=f"ocr:{order.id}"),
                   Btn("📜 Чат", callback_data=f"och:{order.id}"))
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

    def on_payout(self, hub, order: Order) -> None:
        self.notify("payout", f"💸 Деньги по сделке {u.code('#' + order.id[:8])} вышли из холда: "
                              f"{u.b(order.seller_amount)}\n«{escape(order.product_title or '')}»")

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

    def _chat_markup(self, chat: Chat) -> InlineKeyboardMarkup:
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(Btn("✉️ Ответить", callback_data=f"chr:{chat.id}"),
               Btn("📝 Заготовки", callback_data=f"ctp:{chat.id}"))
        kb.add(Btn("📜 История", callback_data=f"chv:{chat.id}"),
               Btn("✅ Прочитано", callback_data=f"crd:{chat.id}"))
        kb.add(Btn("🔗 На сайте", url=chat.url))
        return kb

    def on_new_messages(self, hub, chat: Chat, messages: list[ChatMessage]) -> None:
        if hub.blocked(chat.counterpart.username, "Notifications"):
            return
        own = hub.chat_setting("notifyOwnMessages")
        shown = [m for m in messages if not m.by_me or own]
        if not shown:
            return
        lines = [u.notify_line(chat, m) for m in shown[-10:]]
        if len(shown) > 10:
            lines.insert(0, f"<i>…и ещё {len(shown) - 10} раньше</i>")
        self.notify("message", "\n".join(lines), self._chat_markup(chat), izi_chat=chat.id)

    def on_command(self, chat: Chat, msg: ChatMessage, command: str, text: str) -> None:
        body = escape(format_chat_text(text, chat, msg)) if text else \
            f"{u.b(chat.username)} отправил команду {u.code(command)}"
        self.notify("command", f"🤖 {body}", self._chat_markup(chat), izi_chat=chat.id)

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
        h("ORDER_PAYOUT_RELEASED", self.on_payout)
        h("ORDER_DELIVERED", self.on_delivered)
        h("DELIVERY_FAILED", self.on_delivery_failed)
        h("PRODUCT_DISABLED", self.on_product_disabled)
        h("PRODUCT_RESTORED", self.on_product_restored)
        h("STOCK_REFILLED", self.on_stock_refilled)
        h("WEBHOOK_EVENT", self.on_webhook)
        h("NEW_MESSAGES", self.on_new_messages)

    # ------------------------------------------------------------------ меню

    def main_menu(self, page: int = 0) -> InlineKeyboardMarkup:
        page = max(0, min(page, len(MENU_PAGES) - 1))
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(*(Btn(title, callback_data=cb) for title, cb in MENU_PAGES[page]))
        nav = [Btn("◀️", callback_data=f"menu:{page - 1}") if page > 0 else Btn(" ", callback_data="noop"),
               Btn(f"{page + 1}/{len(MENU_PAGES)}", callback_data="noop"),
               Btn("▶️", callback_data=f"menu:{page + 1}") if page < len(MENU_PAGES) - 1
               else Btn(" ", callback_data="noop")]
        kb.row(*nav)
        return kb

    def _back(self, kb: InlineKeyboardMarkup | None = None, to: str = "menu",
              section: str | None = None) -> InlineKeyboardMarkup:
        kb = kb or InlineKeyboardMarkup()
        if to == "menu" and section:
            to = f"menu:{MENU_PAGE_OF.get(section, 0)}"
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

    def _show(self, c: CallbackQuery, text: str, kb: InlineKeyboardMarkup | None = None,
              izi_chat: str | None = None) -> None:
        """Уведомление о сообщении не затираем — открываем раздел новым сообщением."""
        rec = self._reply_map.get((c.message.chat.id, c.message.message_id))
        if not rec or not rec[1]:
            self._edit(c, text, kb)
            msg = c.message
        else:
            self.bot.answer_callback_query(c.id)
            msg = self.send(c.message.chat.id, text, kb)
        if msg and izi_chat:
            # ответ на окно чата тоже уходит собеседнику
            self._remember_reply(msg, izi_chat)

    def switches_view(self) -> tuple[str, InlineKeyboardMarkup]:
        kb = InlineKeyboardMarkup()
        for key, title in GLOBAL_SWITCHES.items():
            kb.add(Btn(f"{_onoff(self.hub.setting(key))} {title}", callback_data=f"swt:{key}"))
        return "⚙️ <b>Глобальные переключатели</b>", self._back(kb, section="sw")

    def notify_view(self, chat_id: int) -> tuple[str, InlineKeyboardMarkup]:
        prefs = self.chats.get(str(chat_id), {})
        kb = InlineKeyboardMarkup()
        for key, title in NOTIFY_KINDS.items():
            kb.add(Btn(f"{_onoff(prefs.get(key, True))} {title}", callback_data=f"ntt:{key}"))
        return "🔔 <b>Уведомления в этот чат</b>", self._back(kb, section="nt")

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

    # ---- чаты

    def chats_view(self, unread: bool = False) -> tuple[str, InlineKeyboardMarkup]:
        if not self.hub.chats_available:
            return ("💬 Чаты недоступны: у ключа API нет прав chats:read / chats:write.\n"
                    "Выпустите новый ключ, отметив эти права, и пропишите его в configs/_main.cfg."), self._back()
        items, _ = self.hub.client.list_chats(unread_only=unread, limit=20)
        kb = InlineKeyboardMarkup()
        for ch in items:
            mark = f"🔵{ch.unread_count} " if ch.unread_count else ""
            kind = "🛒 " if ch.type == "order" else ""
            last = ch.last_message.text.replace("\ufffc", "🖼").strip()[:25] if ch.last_message else ""
            kb.add(Btn(f"{mark}{kind}{ch.username[:20]}: {last}", callback_data=f"chv:{ch.id}"))
        kb.add(Btn("📋 Все" if unread else "🔵 Только непрочитанные", callback_data=f"chl:{0 if unread else 1}"),
               Btn("🔄", callback_data=f"chl:{1 if unread else 0}"))
        title = "💬 <b>Непрочитанные чаты</b>" if unread else "💬 <b>Последние чаты</b>"
        return (title if items else title + "\n\nПусто"), self._back(kb, section="chl")

    def chat_view(self, chat_id: str, n: int = 15) -> tuple[str, InlineKeyboardMarkup]:
        chat = self.hub.client.get_chat(chat_id)
        msgs, _ = self.hub.client.list_chat_messages(chat_id, limit=n)
        lines = [u.chat_title(chat)]
        for m in msgs:
            when = m.created_at.astimezone().strftime("%d.%m %H:%M") if m.created_at else ""
            lines.append(f"\n<i>{when}</i> {u.author_label(chat, m)}\n{u.message_body(m, 500)}")
        if chat.can_write is False:
            lines.append(f"\n🔒 Писать нельзя: {u.code(chat.write_blocked_reason or '?')}")
        text = "\n".join(lines)
        if len(text) > 3900:  # Telegram режет длинное — оставляем свежие сообщения
            text = lines[0] + "\n…" + text[-(3800 - len(lines[0])):]
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(Btn("✉️ Ответить", callback_data=f"chr:{chat.id}"),
               Btn("📝 Заготовки", callback_data=f"ctp:{chat.id}"))
        kb.add(Btn("✅ Прочитано", callback_data=f"crd:{chat.id}"),
               Btn("🔄 Обновить", callback_data=f"chv:{chat.id}"))
        if chat.counterpart.username:
            bl = self.hub.is_blacklisted(chat.counterpart.username)
            kb.add(Btn("✅ Убрать из ЧС" if bl else "🚫 В чёрный список", callback_data=f"cbl:{chat.id}"))
        if chat.order_id:
            kb.add(Btn("🧾 Сделка", callback_data=f"ord:{chat.order_id}"), Btn("🔗 На сайте", url=chat.url))
        else:
            kb.add(Btn("🔗 На сайте", url=chat.url))
        return text, self._back(kb, "chl:0")

    @property
    def templates(self) -> list[str]:
        return self.hub.store.get("answer_templates") or []

    def templates_view(self) -> tuple[str, InlineKeyboardMarkup]:
        kb = InlineKeyboardMarkup()
        for i, t in enumerate(self.templates):
            kb.add(Btn(f"🗑 {t.replace(chr(10), ' ')[:50]}", callback_data=f"tpd:{i}"))
        kb.add(Btn("➕ Добавить заготовку", callback_data="tpa"))
        text = ("📝 <b>Заготовки ответов</b>\nОтправляются кнопкой «📝 Заготовки» под уведомлением о сообщении. "
                f"Переменные: {CHAT_VARS}.\nНажмите на заготовку, чтобы удалить её.")
        return text, self._back(kb, section="tpl")

    def chat_templates_view(self, chat_id: str) -> tuple[str, InlineKeyboardMarkup]:
        kb = InlineKeyboardMarkup()
        for i, t in enumerate(self.templates):
            kb.add(Btn(t.replace("\n", " ")[:60], callback_data=f"cts:{i}:{chat_id}"))
        if not self.templates:
            kb.add(Btn("➕ Добавить заготовку", callback_data="tpa"))
        return "📝 Выберите заготовку — она сразу уйдёт собеседнику", self._back(kb, f"chv:{chat_id}")

    def ar_view(self, page: int = 0) -> tuple[str, InlineKeyboardMarkup]:
        sections = self.hub.AR_CFG.sections()
        per = 10
        kb = InlineKeyboardMarkup()
        for i, sec in enumerate(sections[page * per:(page + 1) * per], start=page * per):
            kb.add(Btn(f"{_onoff(not is_true(self.hub.AR_CFG.get(sec, 'disable')))} {sec[:50]}",
                       callback_data=f"are:{i}"))
        nav = []
        if page > 0:
            nav.append(Btn("⬅️", callback_data=f"ar:{page - 1}"))
        if (page + 1) * per < len(sections):
            nav.append(Btn("➡️", callback_data=f"ar:{page + 1}"))
        if nav:
            kb.row(*nav)
        kb.add(Btn("➕ Добавить команду", callback_data="ara"))
        text = (f"🤖 <b>Автоответчик</b> — {len(sections)} команд\n"
                f"Включён: {_onoff(self.hub.chat_setting('autoResponse'))}\n"
                "Когда собеседник пишет команду, бот отвечает заданным текстом. "
                "Файл: configs/auto_response.cfg")
        return text, self._back(kb, section="ar")

    def ar_edit_view(self, idx: int) -> tuple[str, InlineKeyboardMarkup]:
        sec = self.hub.AR_CFG.sections()[idx]
        s = self.hub.AR_CFG[sec]
        text = (f"🤖 Команда {u.code(sec)}\n\nОтвет:\n<code>{escape(s.get('response') or '—')}</code>"
                + (f"\n\nТекст уведомления:\n<code>{escape(s.get('notificationText'))}</code>"
                   if s.get("notificationText") else ""))
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(Btn(f"{_onoff(not is_true(s.get('disable')))} Включена", callback_data=f"art:{idx}:disable"))
        kb.add(Btn(f"{_onoff(is_true(s.get('contains')))} Срабатывать, если команда внутри текста",
                   callback_data=f"art:{idx}:contains"))
        kb.add(Btn(f"{_onoff(is_true(s.get('telegramNotification')))} Уведомлять в Telegram",
                   callback_data=f"art:{idx}:telegramNotification"))
        kb.add(Btn("✏️ Изменить ответ", callback_data=f"arr:{idx}"),
               Btn("✏️ Текст уведомления", callback_data=f"arn:{idx}"))
        kb.add(Btn("🗑 Удалить", callback_data=f"ard:{idx}"))
        return text, self._back(kb, "ar:0")

    def chat_settings_view(self) -> tuple[str, InlineKeyboardMarkup]:
        c = self.hub.MAIN_CFG["Chat"]
        kb = InlineKeyboardMarkup(row_width=1)
        for key, title in CHAT_SWITCHES.items():
            kb.add(Btn(f"{_onoff(self.hub.chat_setting(key))} {title}", callback_data=f"cst:{key}"))
        kb.row(*(Btn(f"✏️ {title}", callback_data=f"csx:{key}") for key, title in CHAT_TEXTS.items()))
        kb.row(Btn("💧 Водяной знак", callback_data="csx:watermark"),
               Btn(f"⏱ Кулдаун: {c.get('greetingsCooldown')} дн.", callback_data="csx:greetingsCooldown"))
        who = "тем, кто пишет впервые" if self.hub.chat_setting("greetingsNewOnly") else \
            f"новым и молчавшим {c.get('greetingsCooldown')} дн."
        watermark = self.hub.MAIN_CFG.get("Other", "watermark")
        text = ("👋 <b>Сообщения, которые бот пишет сам</b>\n\n"
                f"Приветствие ({who}):\n<code>{escape(c.get('greetingsText'))}</code>\n\n"
                f"Новый заказ:\n<code>{escape(c.get('newOrderReplyText'))}</code>\n\n"
                f"Подтверждение заказа:\n<code>{escape(c.get('orderConfirmReplyText'))}</code>\n\n"
                f"Водяной знак: {u.code(watermark) if watermark else '—'}")
        if not self.hub.chats_available:
            text += "\n\n⚠️ У ключа API нет прав на чаты — сообщения не отправляются."
        return text, self._back(kb, section="chs")

    def blacklist_view(self) -> tuple[str, InlineKeyboardMarkup]:
        kb = InlineKeyboardMarkup()
        for key, title in BLACKLIST_SWITCHES.items():
            kb.add(Btn(f"{_onoff(self.hub.MAIN_CFG.getboolean('Blacklist', key))} {title}",
                       callback_data=f"blt:{key}"))
        for name in self.hub.blacklist[:40]:
            kb.add(Btn(f"❌ {name}", callback_data=f"bld:{name}"[:64]))
        kb.add(Btn("➕ Добавить пользователя", callback_data="bla"))
        text = (f"🚫 <b>Чёрный список</b> — {len(self.hub.blacklist)} чел.\n"
                "Нажмите на ник, чтобы убрать его из списка.")
        return text, self._back(kb, section="bl")

    def plugins_view(self) -> tuple[str, InlineKeyboardMarkup]:
        kb = InlineKeyboardMarkup()
        for uuid, p in self.hub.plugins.items():
            kb.add(Btn(f"{_onoff(p.enabled)} {p.name} v{p.version}", callback_data=f"plt:{uuid}"[:64]))
        kb.add(Btn("➕ Добавить плагин", callback_data="pladd"))
        text = ("🧩 <b>Плагины</b>\n\n⚠️ Ставьте плагины только из проверенных источников: "
                "плагин получает полный доступ к компьютеру и ключу API.")
        return text, self._back(kb, section="pl")

    def about_text(self) -> str:
        from hub import AUTHOR, AUTHOR_LINK, VERSION
        up = int(time.time() - self.hub.start_time)
        return (f"🤖 <b>IziMarketHub</b> v{VERSION}\n"
                f"Автор: <a href=\"{AUTHOR_LINK}\">{AUTHOR}</a>\n"
                f"Аккаунт: {u.b(self.hub.me.get('username', '?'))}\n"
                f"Работает: {up // 3600} ч {up % 3600 // 60} мин\n"
                f"Плагинов: {len(self.hub.plugins)}\n"
                f"Репозиторий: <a href=\"{updater.REPO_URL}\">GitHub</a>")

    def update_view(self) -> tuple[str, InlineKeyboardMarkup]:
        commits = updater.pending_commits()
        kb = InlineKeyboardMarkup()
        if not commits:
            return "✅ У вас последняя версия IziMarketHub", self._back(kb, section="upd")
        shown = "\n".join(f"• {escape(c)}" for c in commits[:15])
        more = f"\n…и ещё {len(commits) - 15}" if len(commits) > 15 else ""
        kb.add(Btn("⬇️ Обновить и перезапустить", callback_data="updgo"))
        return (f"🔄 <b>Доступно обновление</b> ({len(commits)} изм.)\n\n{shown}{more}\n\n"
                "Настройки, товары и логи не затрагиваются."), self._back(kb, section="upd")

    def _restart(self, chat_id: int, text: str) -> None:
        self.send(chat_id, text)
        self.hub.store.set("restart_notify", chat_id)
        # даём Telegram отправить сообщение, потом заменяем процесс
        threading.Timer(1.5, updater.restart).start()

    # ------------------------------------------------------------------ данные

    def balance_text(self) -> str:
        bal = self.hub.client.get_balance()
        lines = [f"💰 <b>Баланс кошелька</b>",
                 f"Всего: {u.b(bal.balance)}",
                 f"Доступно: {u.b(bal.available)}",
                 f"Заморожено операциями: {escape(str(bal.held))}"]
        if bal.spend_only and bal.spend_only.amount_minor:
            lines.append(f"Только на покупки: {escape(str(bal.spend_only))}")
        # API баланса не отдаёт деньги продаж в холде — считаем их по сделкам
        try:
            h = self.hub.sales_on_hold()
        except (IziAPIError, NetworkError) as e:
            lines.append(f"\n🧊 Холд по продажам посчитать не удалось: {escape(str(e))}")
            return "\n".join(lines)
        lines += ["", "🧊 <b>Холд по продажам</b>",
                  f"В незакрытых сделках: {u.b(h['in_deals'])} ({h['in_deals_count']} шт.)",
                  f"Ждут выплаты: {u.b(h['awaiting'])} ({h['awaiting_count']} шт.)"]
        if h["nearest_payout"]:
            lines.append(f"Ближайшая выплата: {h['nearest_payout'].astimezone().strftime('%d.%m %H:%M')}")
        if h["held_count"]:
            lines.append(f"🔒 Задержано площадкой: {u.b(h['held'])} ({h['held_count']} шт.)")
        lines.append(f"Итого в холде: {u.b(h['total'])}")
        return "\n".join(lines)

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
        period = a.get("period") or {}
        lines = [f"📊 <b>За 7 дней</b> ({period.get('from', '?')} — {period.get('to', '?')})"]
        labels = self._metric_labels()
        cur, prev = a.get("current") or {}, a.get("previous") or {}
        for k, v in cur.items():
            lines.append(f"• {escape(labels.get(k, k))}: {u.b(_fmt_metric(v, k))} "
                         f"(было {escape(_fmt_metric(prev.get(k), k))})")
        return "\n".join(lines)

    def _metric_labels(self) -> dict[str, str]:
        if not getattr(self, "_labels", None):
            try:
                cat = self.hub.client.get_analytics_metrics()
                self._labels = {m["key"]: m.get("label") or m["key"] for m in cat.get("metrics", [])}
            except (IziAPIError, NetworkError, KeyError, TypeError):
                return {}
        return self._labels

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
        bot.message_handler(commands=["chats"])(self._guard(lambda m: self.send(m.chat.id, *self.chats_view())))

        @bot.message_handler(commands=["update"])
        @self._guard
        def update_cmd(m: Message):
            self.send(m.chat.id, *self.update_view())

        @bot.message_handler(commands=["restart"])
        @self._guard
        def restart_cmd(m: Message):
            self._restart(m.chat.id, "🔁 Перезапускаюсь…")

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
            if action not in ("gadd", "pladd", "cfgup"):
                return self.send(m.chat.id, "Файл не ожидался. Откройте нужный пункт меню и нажмите «Добавить».")
            data = bot.download_file(bot.get_file(m.document.file_id).file_path)
            if action == "cfgup":
                self._upload_config(m.chat.id, arg, data)
            elif action == "gadd":
                self._add_goods(m.chat.id, arg, data.decode("utf-8", "replace").splitlines())
            else:
                self._save_plugin(m.chat.id, m.document.file_name, data)

        @bot.message_handler(content_types=["photo"])
        @self._guard
        def photo(m: Message):
            izi_chat = self._reply_target(m)
            if not izi_chat:
                return self.send(m.chat.id, "Картинка не ожидалась. Чтобы отправить её собеседнику, ответьте "
                                            "ею на уведомление о сообщении или нажмите «✉️ Ответить».")
            data = bot.download_file(bot.get_file(m.photo[-1].file_id).file_path)
            up = self.hub.client.upload_chat_image(data, "photo.jpg")
            caption = (m.caption or "").strip()
            self._send_to_chat(m.chat.id, izi_chat, (caption + "\n" if caption else "") + "\ufffc", [up["id"]])

        @bot.message_handler(func=lambda m: True, content_types=["text"])
        def text(m: Message):
            if not self.authorized(m.chat.id):
                return self._try_login(m)
            if m.chat.id in self._pending:
                return self._guard(self._handle_pending)(m)
            izi_chat = self._reply_target(m)
            if izi_chat:
                return self._guard(lambda msg: self._send_to_chat(msg.chat.id, izi_chat, msg.text))(m)
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

    def _reply_target(self, m: Message) -> str | None:
        """Чат IziMarket, куда отправить сообщение: ответ на уведомление или нажатая «✉️ Ответить»."""
        if m.chat.id in self._pending and self._pending[m.chat.id][0] == "chr":
            return self._pending.pop(m.chat.id)[1]
        r = m.reply_to_message
        if r:
            rec = self._reply_map.get((m.chat.id, r.message_id))
            return rec[0] if rec else None
        return None

    def _send_to_chat(self, tg_chat: int, izi_chat: str, text: str, images: list[str] | None = None) -> None:
        try:
            if images:
                self.hub.send_message(izi_chat, text, images=images, by_bot=False)
            else:
                self.hub.send_text(izi_chat, text, by_bot=False)
        except IziAPIError as e:
            return self.send(tg_chat, f"❌ Не отправлено: {escape(e.message or str(e))}"
                                      + (f" ({u.code(e.code)})" if e.code else ""))
        kb = InlineKeyboardMarkup().add(Btn("📜 История", callback_data=f"chv:{izi_chat}"))
        self.send(tg_chat, "✅ Отправлено", kb)

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
        elif action == "chr":
            self._send_to_chat(m.chat.id, arg, txt)
        elif action == "tpa":
            if txt.strip():
                self.hub.store.update("answer_templates", lambda old: (old or []) + [txt.strip()])
            self.send(m.chat.id, *self.templates_view())
        elif action == "ara":
            cmd = " ".join(txt.lower().split())
            if not cmd or "[" in cmd or "]" in cmd:
                return self.send(m.chat.id, "Команда не может быть пустой и содержать [ ]")
            if not self.hub.AR_CFG.has_section(cmd):
                self.hub.AR_CFG.add_section(cmd)
                for k, (default, _) in AR_SCHEMA.items():
                    self.hub.AR_CFG.set(cmd, k, default)
            idx = self.hub.AR_CFG.sections().index(cmd)
            self._ask(m.chat.id, "arr", str(idx), f"✏️ Теперь отправьте ответ на {u.code(cmd)}. "
                                                  f"Переменные: {CHAT_VARS}")
        elif action in ("arr", "arn"):
            sec = self.hub.AR_CFG.sections()[int(arg)]
            self.hub.AR_CFG.set(sec, "response" if action == "arr" else "notificationText", txt.replace("\n", "\\n"))
            if action == "arn":
                self.hub.AR_CFG.set(sec, "telegramNotification", "1")
            self.hub.save_ar_config()
            self.send(m.chat.id, *self.ar_edit_view(int(arg)))
        elif action == "csx":
            section = "Other" if arg == "watermark" else "Chat"
            value = "" if arg == "watermark" and txt.strip() == "-" else txt.replace("\n", "\\n")
            if arg == "greetingsCooldown":
                if not value.strip().isdigit():
                    return self.send(m.chat.id, "Нужно целое число дней")
                value = value.strip()
            self.hub.MAIN_CFG.set(section, arg, value)
            self.hub.save_main_config()
            self.send(m.chat.id, *self.chat_settings_view())
        elif action == "bla":
            for name in txt.replace(",", " ").split():
                self.hub.blacklist_add(name)
            self.send(m.chat.id, *self.blacklist_view())
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

    def _upload_config(self, chat_id: int, key: str, data: bytes) -> None:
        from Utils import config_loader as cl
        name, loader, attr = CONFIG_FILES[key]
        path = os.path.join(cl.CONFIG_DIR, name)
        tmp = path + ".upload"
        os.makedirs(cl.CONFIG_DIR, exist_ok=True)
        with open(tmp, "wb") as f:
            f.write(data)
        try:
            cfg = getattr(cl, loader)(tmp)
        except Exception as e:  # ConfigError или битый INI
            os.remove(tmp)
            return self.send(chat_id, f"❌ Конфиг не принят: {escape(str(e))}")
        os.replace(tmp, path)
        setattr(self.hub, attr, cfg)
        logger.warning(f"Через Telegram загружен {name}")
        self.send(chat_id, f"✅ {u.code(name)} загружен и применён: {len(cfg.sections())} секций")

    def configs_view(self) -> tuple[str, InlineKeyboardMarkup]:
        kb = InlineKeyboardMarkup(row_width=2)
        for key, (name, _, _) in CONFIG_FILES.items():
            kb.add(Btn(f"📤 {name}", callback_data=f"cfgget:{key}"), Btn("📥 Загрузить", callback_data=f"cfgup:{key}"))
        text = ("📂 <b>Конфиги</b>\nСкачайте файл, поправьте и загрузите обратно — бот проверит его "
                "и применит без перезапуска.")
        return text, self._back(kb, section="cfg")

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

        if cmd == "noop":
            return self.bot.answer_callback_query(c.id)
        if cmd == "menu":
            return self._edit(c, "📋 <b>Меню IziMarketHub</b>", self.main_menu(int(arg or 0)))
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
        if cmd == "chl":
            return self._edit(c, *self.chats_view(arg == "1"))
        if cmd == "chv":
            return self._show(c, *self.chat_view(arg), izi_chat=arg)
        if cmd == "chr":
            self.bot.answer_callback_query(c.id)
            return self._ask(chat_id, "chr", arg, "✉️ Отправьте текст или картинку — уйдёт собеседнику")
        if cmd == "ctp":
            return self._show(c, *self.chat_templates_view(arg))
        if cmd == "cts":
            idx, izi_chat = arg.split(":", 1)
            tpls = self.templates
            if int(idx) >= len(tpls):
                return self.bot.answer_callback_query(c.id, "Заготовка удалена")
            self.bot.answer_callback_query(c.id)
            chat = hub.client.get_chat(izi_chat)
            return self._send_to_chat(chat_id, izi_chat, format_chat_text(tpls[int(idx)], chat))
        if cmd == "crd":
            r = hub.client.mark_chat_read(arg)
            return self.bot.answer_callback_query(c.id, f"Прочитано, непрочитанных: {r.get('unread_count', 0)}")
        if cmd == "cbl":
            chat = hub.client.get_chat(arg)
            name = chat.counterpart.username
            if name:
                hub.blacklist_remove(name) if hub.is_blacklisted(name) else hub.blacklist_add(name)
            return self._edit(c, *self.chat_view(arg))
        if cmd == "ord":
            order = hub.client.get_order(arg)
            self.bot.answer_callback_query(c.id)
            return self.send(chat_id, u.order_text(order, "🧾 Сделка"), self._order_markup(order))
        if cmd == "tpl":
            return self._edit(c, *self.templates_view())
        if cmd == "tpa":
            self.bot.answer_callback_query(c.id)
            return self._ask(chat_id, "tpa", "", f"📝 Отправьте текст заготовки. Переменные: {CHAT_VARS}")
        if cmd == "tpd":
            i = int(arg)
            hub.store.update("answer_templates", lambda old: [t for j, t in enumerate(old or []) if j != i])
            return self._edit(c, *self.templates_view())
        if cmd == "ar":
            return self._edit(c, *self.ar_view(int(arg or 0)))
        if cmd == "are":
            return self._edit(c, *self.ar_edit_view(int(arg)))
        if cmd == "art":
            idx, key = arg.split(":")
            sec = hub.AR_CFG.sections()[int(idx)]
            hub.AR_CFG.set(sec, key, "0" if is_true(hub.AR_CFG.get(sec, key)) else "1")
            hub.save_ar_config()
            return self._edit(c, *self.ar_edit_view(int(idx)))
        if cmd == "ara":
            self.bot.answer_callback_query(c.id)
            return self._ask(chat_id, "ara", "", "🤖 Отправьте команду, на которую отвечать (например, !помощь). "
                                                 "Несколько вариантов — через |")
        if cmd in ("arr", "arn"):
            self.bot.answer_callback_query(c.id)
            what = "ответ на команду" if cmd == "arr" else "текст уведомления в Telegram"
            return self._ask(chat_id, cmd, arg, f"✏️ Отправьте {what}. Переменные: {CHAT_VARS}")
        if cmd == "ard":
            hub.AR_CFG.remove_section(hub.AR_CFG.sections()[int(arg)])
            hub.save_ar_config()
            return self._edit(c, *self.ar_view(0))
        if cmd == "chs":
            return self._edit(c, *self.chat_settings_view())
        if cmd in ("ocr", "och"):
            chat = hub.client.find_order_chat(arg)
            if not chat:
                return self.bot.answer_callback_query(c.id, "Чата по этой сделке пока нет", show_alert=True)
            if cmd == "och":
                self.bot.answer_callback_query(c.id)
                text, kb = self.chat_view(chat.id)
                msg = self.send(chat_id, text, kb)
                if msg:
                    self._remember_reply(msg, chat.id)
                return
            self.bot.answer_callback_query(c.id)
            return self._ask(chat_id, "chr", chat.id, f"✉️ Сообщение покупателю {u.b(chat.username)} — "
                                                      "текст или картинка")
        if cmd == "cfg":
            return self._edit(c, *self.configs_view())
        if cmd == "cfgget":
            from Utils import config_loader as cl
            self.bot.answer_callback_query(c.id)
            path = os.path.join(cl.CONFIG_DIR, CONFIG_FILES[arg][0])
            if not os.path.exists(path):
                return self.send(chat_id, f"Файла {u.code(CONFIG_FILES[arg][0])} ещё нет")
            with open(path, "rb") as f:
                self.bot.send_document(chat_id, f, visible_file_name=CONFIG_FILES[arg][0])
            return
        if cmd == "cfgup":
            self.bot.answer_callback_query(c.id)
            return self._ask(chat_id, "cfgup", arg, f"📥 Отправьте файл {u.code(CONFIG_FILES[arg][0])}")
        if cmd == "cst":
            hub.toggle_setting("Chat", arg)
            return self._edit(c, *self.chat_settings_view())
        if cmd == "csx":
            self.bot.answer_callback_query(c.id)
            if arg == "watermark":
                return self._ask(chat_id, "csx", arg, "✏️ Отправьте водяной знак — он встанет первой строкой "
                                                      "в автоматических сообщениях. «-» — убрать")
            if arg == "greetingsCooldown":
                return self._ask(chat_id, "csx", arg, "⏱ Через сколько дней тишины здороваться снова "
                                                      "(работает, если выключено «только тем, кто пишет впервые»)")
            variables = CHAT_VARS if arg == "greetingsText" else ORDER_VARS
            return self._ask(chat_id, "csx", arg, f"✏️ Отправьте новый текст. Переменные: {variables}")
        if cmd == "bl":
            return self._edit(c, *self.blacklist_view())
        if cmd == "blt":
            hub.toggle_setting("Blacklist", arg)
            return self._edit(c, *self.blacklist_view())
        if cmd == "bld":
            hub.blacklist_remove(arg)
            return self._edit(c, *self.blacklist_view())
        if cmd == "bla":
            self.bot.answer_callback_query(c.id)
            return self._ask(chat_id, "bla", "", "🚫 Отправьте ник (или несколько через пробел)")
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
        if cmd == "upd":
            self._edit(c, "🔄 Проверяю обновления…")
            return self._edit(c, *self.update_view())
        if cmd == "updgo":
            self._edit(c, "⏳ Обновляюсь…")
            commits = updater.update()
            if not commits:
                return self._edit(c, "✅ Уже последняя версия", self._back(section="upd"))
            self._edit(c, f"✅ Обновлено ({len(commits)} изм.)")
            return self._restart(chat_id, "🔁 Перезапускаюсь на новую версию…")
        if cmd == "about":
            return self._edit(c, self.about_text(), self._back(section="about"))
        self.bot.answer_callback_query(c.id, "Неизвестная кнопка")

    # ------------------------------------------------------------------ запуск

    def start(self) -> None:
        try:
            self.bot.set_my_commands([
                BotCommand("menu", "Меню"), BotCommand("chats", "Чаты"), BotCommand("orders", "Последние сделки"),
                BotCommand("balance", "Баланс"), BotCommand("stats", "Статистика за 7 дней"),
                BotCommand("deliver", "Выдать сделку вручную"), BotCommand("logs", "Файл логов"),
                BotCommand("update", "Обновить бота из GitHub"), BotCommand("restart", "Перезапустить"),
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
        from hub import VERSION
        chat = self.hub.store.get("restart_notify")
        if chat:
            self.hub.store.set("restart_notify", None)
            self.send(chat, f"✅ IziMarketHub v{VERSION} перезапущен")
        self.notify_system("✅ IziMarketHub запущен")
