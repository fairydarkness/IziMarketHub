"""Логи: цветной вывод в консоль и ротация файлов в logs/."""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler

LOG_FILE = os.path.join("logs", "log.log")

_COLORS = {
    logging.DEBUG: "\033[90m",
    logging.INFO: "\033[0m",
    logging.WARNING: "\033[33m",
    logging.ERROR: "\033[31m",
    logging.CRITICAL: "\033[41m",
}


class _ConsoleFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        color = _COLORS.get(record.levelno, "")
        return f"{color}{super().format(record)}\033[0m"


def setup_logging(debug: bool = False) -> None:
    os.makedirs("logs", exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers.clear()

    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG if debug else logging.INFO)
    console.setFormatter(_ConsoleFormatter("[%(asctime)s] %(levelname)-7s %(name)s: %(message)s", "%H:%M:%S"))

    file = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
    file.setLevel(logging.DEBUG)
    file.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(name)s [%(threadName)s]: %(message)s"))

    root.addHandler(console)
    root.addHandler(file)
    for noisy in ("urllib3", "TeleBot"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
