"""Первичная настройка: создаёт configs/_main.cfg и пример configs/auto_delivery.cfg."""

from __future__ import annotations

import os

from IziAPI import Client
from IziAPI.exceptions import IziAPIError, NetworkError
from Utils import config_loader as cl
from tg_bot.utils import hash_password

AD_EXAMPLE = """\
# Автовыдача IziMarketHub.
# Имя секции — id товара (uuid из ссылки https://izi.market/products/<id>) или его точное название.
#
# response            — текст выдачи. Переменные: $username $product $product_title $product_id
#                       $order_id $quantity $amount $seller_amount $date $time $input_<ключ> $param_<N>
#                       Перенос строки — \\n
# productsFileName    — файл в storage/products/, одна строка = одна единица товара
# fields              — ключи полей выдачи подкатегории через запятую: строка "kiwi:melon"
#                       при fields = login,password уйдёт как {"login": "kiwi", "password": "melon"}
# disable             — 1: не выдавать этот товар автоматически
# disableAutoDisable  — 1: не снимать товар с продажи, когда файл опустел
# disableAutoRestore  — 1: не выставлять товар снова, когда в файле появились строки
# stockRefill         — 1: для товара со складом площадки докладывать единицы из файла на склад
#
# [01a13c13-f761-7231-92ec-6f80bf741643]
# response = Спасибо за покупку, $username!\\nВаш ключ:\\n$product
# productsFileName = hades.txt
"""


def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or default


def ask_bool(prompt: str, default: bool) -> bool:
    v = ask(f"{prompt} (y/n)", "y" if default else "n").lower()
    return v in ("y", "yes", "д", "да", "1")


def run_setup() -> None:
    print("=== Первичная настройка IziMarketHub (автор @fairydarkns) ===\n")
    print("Ключ API выпускается на izi.market → Настройки → API → Ключи.")
    print("Нужные права: orders:read, orders:write, products:read, products:write, stock:read, stock:write")
    print("(для статистики и баланса — analytics:read, balance:read).\n")

    while True:
        key = ask("Ключ API (izp_…)")
        if not key.startswith("izp_"):
            print("Ключ должен начинаться с izp_")
            continue
        try:
            me = Client(key).get_me()
        except (IziAPIError, NetworkError) as e:
            print(f"Ключ не подошёл: {e}")
            continue
        print(f"OK: аккаунт {me['username']}, права: {', '.join(me['key']['scopes'])}")
        break

    cfg = cl.new_parser()
    for section, keys in cl.MAIN_SCHEMA.items():
        cfg.add_section(section)
        for k, (default, _) in keys.items():
            cfg.set(section, k, default)
    cfg.set("IziMarket", "apiKey", key)

    if ask_bool("\nПодключить Telegram-бота для уведомлений и управления?", True):
        print("Создайте бота у @BotFather и вставьте токен.")
        cfg.set("Telegram", "enabled", "1")
        cfg.set("Telegram", "token", ask("Токен бота"))
        while True:
            pwd = ask("Пароль доступа к боту (от 8 символов)")
            if len(pwd) >= 8:
                break
            print("Слишком короткий")
        cfg.set("Telegram", "secretKeyHash", hash_password(pwd))

    if ask_bool("\nВключить приёмник вебхуков? (нужен https-адрес наружу; без него бот опрашивает API)", False):
        cfg.set("Webhook", "enabled", "1")
        cfg.set("Webhook", "port", ask("Порт", "8080"))
        cfg.set("Webhook", "signingSecret", ask("Ключ подписи (izs_…)"))

    cl.save_config(cfg, cl.MAIN_CFG)
    if not os.path.exists(cl.AD_CFG):
        with open(cl.AD_CFG, "w", encoding="utf-8") as f:
            f.write(AD_EXAMPLE)
    try:
        os.chmod(cl.MAIN_CFG, 0o600)
    except OSError:
        pass
    print(f"\nГотово: {cl.MAIN_CFG}. Автовыдача настраивается в {cl.AD_CFG} или из Telegram.")
