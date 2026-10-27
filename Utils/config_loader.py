"""Загрузка и проверка INI-конфигов IziMarketHub."""

from __future__ import annotations

import configparser
import os
import re

CONFIG_DIR = "configs"
MAIN_CFG = os.path.join(CONFIG_DIR, "_main.cfg")
AD_CFG = os.path.join(CONFIG_DIR, "auto_delivery.cfg")
GOODS_DIR = os.path.join("storage", "products")

BOOL_TRUE = {"1", "true", "yes", "on", "да"}
BOOL_VALUES = BOOL_TRUE | {"0", "false", "no", "off", "нет"}

# секция → ключ → (умолчание, проверка)
MAIN_SCHEMA: dict[str, dict[str, tuple[str, str]]] = {
    "IziMarket": {
        "apiKey": ("", "str"),
        "locale": ("ru", "ru|en"),
        "pollInterval": ("15", "int:5"),
        "autoDelivery": ("1", "bool"),
        "autoDisable": ("1", "bool"),
        "autoRestore": ("1", "bool"),
        "stockRefill": ("1", "bool"),
        "syncQuantity": ("0", "bool"),
        "deliverPendingOnStart": ("1", "bool"),
        "proxy": ("", "str"),
    },
    "StockRefill": {
        "checkInterval": ("300", "int:60"),
        "threshold": ("5", "int:0"),
        "batch": ("50", "int:1"),
    },
    "Telegram": {
        "enabled": ("0", "bool"),
        "token": ("", "str"),
        "secretKeyHash": ("", "str"),
        "proxy": ("", "str"),
    },
    "Webhook": {
        "enabled": ("0", "bool"),
        "host": ("127.0.0.1", "str"),
        "port": ("8080", "int:1"),
        "path": ("/izimarket", "str"),
        "signingSecret": ("", "str"),
    },
    "Other": {
        "debug": ("0", "bool"),
        "watermark": ("", "str"),
    },
}

AD_SCHEMA: dict[str, tuple[str, str]] = {
    "response": ("", "str"),
    "productsFileName": ("", "str"),
    "fields": ("", "str"),
    "disable": ("0", "bool"),
    "disableAutoDisable": ("0", "bool"),
    "disableAutoRestore": ("0", "bool"),
    "stockRefill": ("1", "bool"),
}


class ConfigError(Exception):
    pass


def new_parser() -> configparser.ConfigParser:
    p = configparser.ConfigParser(interpolation=None, delimiters=("=",), comment_prefixes=("#", ";"),
                                  inline_comment_prefixes=None, empty_lines_in_values=False)
    p.optionxform = str  # не менять регистр ключей
    return p


def _check(section: str, key: str, value: str, rule: str, path: str) -> None:
    where = f"{path}: [{section}] {key} = {value!r}"
    if rule == "bool":
        if value.strip().lower() not in BOOL_VALUES:
            raise ConfigError(f"{where} — ожидается 0 или 1")
    elif rule.startswith("int"):
        try:
            n = int(value)
        except ValueError:
            raise ConfigError(f"{where} — ожидается целое число") from None
        lo = int(rule.split(":")[1]) if ":" in rule else None
        if lo is not None and n < lo:
            raise ConfigError(f"{where} — минимум {lo}")
    elif "|" in rule and value not in rule.split("|"):
        raise ConfigError(f"{where} — допустимо: {rule.replace('|', ', ')}")


def load_main_config(path: str = MAIN_CFG) -> configparser.ConfigParser:
    if not os.path.exists(path):
        raise ConfigError(f"Нет файла {path}. Запустите первичную настройку: python main.py --setup")
    cfg = new_parser()
    cfg.read(path, encoding="utf-8")
    for section, keys in MAIN_SCHEMA.items():
        if not cfg.has_section(section):
            cfg.add_section(section)
        for key, (default, rule) in keys.items():
            if not cfg.has_option(section, key):
                cfg.set(section, key, default)
            _check(section, key, cfg.get(section, key), rule, path)
    # ключ из окружения важнее файла: удобно для Docker и чтобы не хранить ключ в конфиге
    if os.environ.get("IZI_API_KEY"):
        cfg.set("IziMarket", "apiKey", os.environ["IZI_API_KEY"])
    if os.environ.get("IZI_TG_TOKEN"):
        cfg.set("Telegram", "token", os.environ["IZI_TG_TOKEN"])
    if os.environ.get("IZI_SIGNING_SECRET"):
        cfg.set("Webhook", "signingSecret", os.environ["IZI_SIGNING_SECRET"])
    if not cfg.get("IziMarket", "apiKey").startswith("izp_"):
        raise ConfigError(f"{path}: [IziMarket] apiKey должен начинаться с izp_ (или задайте IZI_API_KEY)")
    if cfg.getboolean("Telegram", "enabled") and not cfg.get("Telegram", "token"):
        raise ConfigError(f"{path}: [Telegram] включён, но token пуст")
    return cfg


def load_auto_delivery_config(path: str = AD_CFG) -> configparser.ConfigParser:
    cfg = new_parser()
    if not os.path.exists(path):
        return cfg
    cfg.read(path, encoding="utf-8")
    for section in cfg.sections():
        for key, (default, rule) in AD_SCHEMA.items():
            if not cfg.has_option(section, key):
                cfg.set(section, key, default)
            _check(section, key, cfg.get(section, key), rule, path)
        unknown = set(cfg.options(section)) - set(AD_SCHEMA)
        if unknown:
            raise ConfigError(f"{path}: [{section}] неизвестные параметры: {', '.join(sorted(unknown))}")
        if not cfg.get(section, "response") and not cfg.get(section, "productsFileName"):
            raise ConfigError(f"{path}: [{section}] нужен response и/или productsFileName")
        fname = cfg.get(section, "productsFileName")
        if fname and not re.fullmatch(r"[\w\-. ]+\.txt", fname):
            raise ConfigError(f"{path}: [{section}] productsFileName — имя .txt файла из {GOODS_DIR}")
    return cfg


def save_config(cfg: configparser.ConfigParser, path: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        cfg.write(f)
    os.replace(tmp, path)


def is_true(value: str | None) -> bool:
    return (value or "").strip().lower() in BOOL_TRUE
