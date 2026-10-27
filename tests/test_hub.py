import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.request

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fake_api import FakeAPI  # noqa: E402
from IziAPI import Client, Order, verify_signature  # noqa: E402
from Utils import config_loader as cl  # noqa: E402
from Utils.storage import GoodsStorage  # noqa: E402
from Utils.templates import format_text  # noqa: E402

P_MANUAL = "11111111-1111-4111-8111-111111111111"
P_STOCK = "22222222-2222-4222-8222-222222222222"


@pytest.fixture
def api():
    a = FakeAPI()
    yield a
    a.close()


@pytest.fixture
def hub(api, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    os.makedirs("configs")
    cfg = cl.new_parser()
    for section, keys in cl.MAIN_SCHEMA.items():
        cfg.add_section(section)
        for k, (default, _) in keys.items():
            cfg.set(section, k, default)
    cfg.set("IziMarket", "apiKey", "izp_test")
    cl.save_config(cfg, cl.MAIN_CFG)
    with open(cl.AD_CFG, "w", encoding="utf-8") as f:
        f.write(f"[{P_MANUAL}]\nresponse = Привет, $username ($input_nick)!\\n$product\nproductsFileName = keys.txt\n\n"
                f"[Ключ на складе]\nproductsFileName = stock.txt\n")

    from handlers import register_handlers
    from hub import IziMarketHub
    h = IziMarketHub(cl.load_main_config(), cl.load_auto_delivery_config())
    h.client = Client("izp_test", base_url=api.url, max_retries=1)
    register_handlers(h)
    h.events = []
    for e in ("NEW_ORDER", "ORDER_DELIVERED", "DELIVERY_FAILED", "PRODUCT_DISABLED", "PRODUCT_RESTORED",
              "STOCK_REFILLED", "ORDER_STATUS_CHANGED"):
        h.add_handler(e, lambda hub, *a, _e=e: hub.events.append((_e, a)))
    return h


def test_signature():
    body = b'{"id":"e1","type":"order.created"}'
    ts = str(int(time.time()))
    sig = hmac.new(b"izs_secret", ts.encode() + b"." + body, hashlib.sha256).hexdigest()
    assert verify_signature("izs_secret", ts, f"v1={sig}", body)
    assert verify_signature("izs_secret", ts, f"v1=deadbeef, v1={sig}", body)
    assert not verify_signature("izs_other", ts, f"v1={sig}", body)
    assert not verify_signature("izs_secret", ts, f"v1={sig}", body + b" ")
    old = str(int(time.time()) - 600)
    old_sig = hmac.new(b"izs_secret", old.encode() + b"." + body, hashlib.sha256).hexdigest()
    assert not verify_signature("izs_secret", old, f"v1={old_sig}", body)


def test_templates():
    order = Order.from_dict({"id": "o1", "status": "paid", "product_id": "p", "product_title": "Robux",
                             "quantity": 2, "buyer": {"username": "kiwi", "inputs": {"nick": "k1"},
                                                      "parameters": [{"group_id": 12, "value": "EU",
                                                                      "options": []}]}})
    text = format_text("Hi $username/$input_nick/$param_12: $product_title x$quantity\\n$product", order,
                       ["A", "B"])
    assert text == "Hi kiwi/k1/EU: Robux x2\nA\nB"


def test_goods_take_give_back(tmp_path):
    g = GoodsStorage(str(tmp_path))
    g.add("a.txt", ["1", "2", " ", "3"])
    assert g.count("a.txt") == 3
    assert g.take("a.txt", 4) is None
    assert g.take("a.txt", 2) == ["1", "2"]
    g.give_back("a.txt", ["1", "2"])
    assert g.peek("a.txt") == ["1", "2", "3"]


def test_config_validation(tmp_path):
    p = tmp_path / "ad.cfg"
    p.write_text("[x]\nresponse = hi\ndisable = maybe\n", encoding="utf-8")
    with pytest.raises(cl.ConfigError):
        cl.load_auto_delivery_config(str(p))
    p.write_text("[x]\nresponse = hi\nfoo = 1\n", encoding="utf-8")
    with pytest.raises(cl.ConfigError):
        cl.load_auto_delivery_config(str(p))


def test_auto_delivery_and_disable(api, hub):
    api.add_product(P_MANUAL, "Ключ Hades")
    hub.goods.add("keys.txt", ["KEY-1", "KEY-2\\nline2"])
    hub.init()
    hub.poll_orders()  # курсор = сейчас, сделок нет

    api.add_order("o1", P_MANUAL, quantity=2)
    hub.poll_orders()

    o = api.orders["o1"]
    assert o["status"] == "delivered"
    assert o["delivered"]["content"] == "Привет, kiwi (kiwi_game)!\nKEY-1\nKEY-2\nline2"
    assert hub.goods.count("keys.txt") == 0
    assert api.products[P_MANUAL]["status"] == "hidden"  # автодеактивация
    names = [e for e, _ in hub.events]
    assert names.count("NEW_ORDER") == 1 and "ORDER_DELIVERED" in names and "PRODUCT_DISABLED" in names

    # повторный опрос: та же сделка с новым updated_at не выдаётся второй раз
    delivers_before = sum(1 for m, p, _ in api.calls if p.endswith("/deliver"))
    hub.poll_orders()
    assert sum(1 for m, p, _ in api.calls if p.endswith("/deliver")) == delivers_before
    assert "ORDER_STATUS_CHANGED" not in [e for e, _ in hub.events]

    # автовосстановление: строки появились — товар снова выставлен
    hub.goods.add("keys.txt", ["KEY-3"])
    hub.check_restore()
    assert api.products[P_MANUAL]["status"] == "active"
    assert "PRODUCT_RESTORED" in [e for e, _ in hub.events]


def test_not_enough_goods(api, hub):
    api.add_product(P_MANUAL, "Ключ Hades")
    hub.goods.add("keys.txt", ["KEY-1"])
    hub.poll_orders()
    api.add_order("o2", P_MANUAL, quantity=3)
    hub.poll_orders()
    assert api.orders["o2"]["status"] == "paid"
    assert hub.goods.count("keys.txt") == 1
    assert "DELIVERY_FAILED" in [e for e, _ in hub.events]


def test_conflict_returns_goods(api, hub):
    api.add_product(P_MANUAL, "Ключ Hades")
    hub.goods.add("keys.txt", ["KEY-1", "KEY-2"])
    hub.poll_orders()
    api.deliver_status = 409
    api.add_order("o3", P_MANUAL)
    hub.poll_orders()
    assert hub.goods.peek("keys.txt") == ["KEY-1", "KEY-2"]
    assert "DELIVERY_FAILED" in [e for e, _ in hub.events]


def test_pending_on_start(api, hub):
    api.add_product(P_MANUAL, "Ключ Hades")
    hub.goods.add("keys.txt", ["KEY-1"])
    api.add_order("old", P_MANUAL)
    hub.process_pending_on_start()
    assert api.orders["old"]["status"] == "delivered"


def test_stock_product_is_left_to_platform_and_refilled(api, hub):
    api.add_product(P_STOCK, "Ключ на складе", stock=True, quantity=1)
    hub.goods.add("stock.txt", [f"S-{i}" for i in range(7)])
    hub.poll_orders()
    api.add_order("o4", P_STOCK)
    hub.poll_orders()
    assert api.orders["o4"]["status"] == "paid"  # выдаёт площадка, не бот

    from handlers import refill_stock_all
    refill_stock_all(hub)  # секция по названию → id товара через список
    assert api.stock[P_STOCK] == [f"S-{i}" for i in range(7)]
    assert hub.goods.count("stock.txt") == 0
    assert "STOCK_REFILLED" in [e for e, _ in hub.events]


def test_webhook_server(hub):
    from webhook_server import WebhookServer
    hub.MAIN_CFG.set("Webhook", "signingSecret", "izs_secret")
    hub.MAIN_CFG.set("Webhook", "port", "0")
    srv = WebhookServer(hub)
    srv.port = 0
    got = []
    hub.add_handler("WEBHOOK_EVENT", lambda h, ev: got.append(ev.type))
    srv.start()
    port = srv.httpd.server_port
    body = json.dumps({"id": "e1", "type": "order.created", "data": {}}).encode()
    ts = str(int(time.time()))
    sig = hmac.new(b"izs_secret", ts.encode() + b"." + body, hashlib.sha256).hexdigest()

    def post(signature):
        req = urllib.request.Request(f"http://127.0.0.1:{port}/izimarket", data=body, method="POST", headers={
            "X-IziMarket-Timestamp": ts, "X-IziMarket-Signature": signature, "X-IziMarket-Event-Id": "e1",
            "Content-Type": "application/json"})
        try:
            return urllib.request.urlopen(req).status
        except urllib.error.HTTPError as e:
            return e.code

    assert post("v1=bad") == 401
    assert post(f"v1={sig}") == 200
    assert post(f"v1={sig}") == 200  # повтор той же доставки
    time.sleep(0.3)
    srv.stop()
    assert got == ["order.created"]
    assert hub._wake_orders.is_set()


def test_tg_menus(api, hub, monkeypatch):
    from types import SimpleNamespace
    from tg_bot.bot import TGBot
    hub.MAIN_CFG.set("Telegram", "token", "123:fake")
    api.add_product(P_MANUAL, "Ключ Hades")
    api.add_product("33333333-3333-4333-8333-333333333333", "Новый товар")
    hub.goods.add("keys.txt", ["K"])
    tg = TGBot(hub)
    tg._authorize(1)
    shown = []
    monkeypatch.setattr(tg, "_edit", lambda c, text, kb=None: shown.append((c.data, text, kb)))
    monkeypatch.setattr(tg, "send", lambda chat, text, markup=None: shown.append(("send", text, markup)))
    tg.bind()  # методы-обработчики регистрируются в ядре
    api.add_order("o0", P_MANUAL)
    hub.dispatch("NEW_ORDER", hub.client.get_order("o0"))
    assert shown and shown[-1][0] == "send" and "Новая сделка" in shown[-1][1]
    monkeypatch.setattr(tg.bot, "answer_callback_query", lambda *a, **k: None)

    def click(data):
        tg._callback(SimpleNamespace(id="1", data=data, message=SimpleNamespace(chat=SimpleNamespace(id=1))))
        return shown[-1]

    for data in ("menu", "sw", "swt:autoDelivery", "nt", "ntt:new_order", "ad:0", "ade:0", "adt:0:disable",
                 "gf", "gfo:keys.txt", "pr:1", f"pro:{P_MANUAL}", f"pun:{P_MANUAL}", f"ppub:{P_MANUAL}",
                 "adb:1", "adbp:33333333-3333-4333-8333-333333333333", "pl", "about"):
        click(data)
    assert hub.setting("autoDelivery") is False
    assert hub.AD_CFG.has_section("33333333-3333-4333-8333-333333333333")
    assert tg.chats["1"]["new_order"] is False
    assert all(len(b.callback_data or "") <= 64 for _, _, kb in shown if kb
               for row in kb.keyboard for b in row)

    # ручная выдача через ожидание ввода
    api.add_order("o9", P_MANUAL)
    click("deliver:o9")
    tg._handle_pending(SimpleNamespace(chat=SimpleNamespace(id=1), text="ручной ключ"))
    assert api.orders["o9"]["delivered"]["content"] == "ручной ключ"
    from tg_bot import utils as u
    h = u.hash_password("secret123")
    assert u.check_password("secret123", h) and not u.check_password("nope", h)
