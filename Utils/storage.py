"""Состояние бота на диске: JSON-хранилище и файлы товаров автовыдачи."""

from __future__ import annotations

import json
import os
import threading
from typing import Any

from .config_loader import GOODS_DIR

STATE_FILE = os.path.join("storage", "cache", "state.json")


class JSONStore:
    """Потокобезопасный словарь, который атомарно пишется на диск при каждом изменении."""

    def __init__(self, path: str = STATE_FILE):
        self.path = path
        self._lock = threading.RLock()
        self._data: dict[str, Any] = {}
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                self._data = json.load(f)

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._data[key] = value
            self._flush()

    def update(self, key: str, fn) -> Any:
        """Атомарно меняет значение: ``value = fn(old)``."""
        with self._lock:
            self._data[key] = fn(self._data.get(key))
            self._flush()
            return self._data[key]

    def _flush(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)


class GoodsStorage:
    """Файлы товаров ``storage/products/*.txt``: одна строка — одна единица товара.

    Внутри строки ``\\n`` превращается в перенос строки при выдаче.
    Выдача идёт в два шага: ``take`` снимает строки с файла, ``give_back`` возвращает их,
    если сделку выдать не удалось.
    """

    def __init__(self, directory: str = GOODS_DIR):
        self.dir = directory
        self._lock = threading.RLock()
        os.makedirs(directory, exist_ok=True)

    def path(self, name: str) -> str:
        name = os.path.basename(name)
        return os.path.join(self.dir, name)

    def files(self) -> list[str]:
        return sorted(f for f in os.listdir(self.dir) if f.endswith(".txt"))

    def _read(self, name: str) -> list[str]:
        p = self.path(name)
        if not os.path.exists(p):
            return []
        with open(p, encoding="utf-8") as f:
            return [line.rstrip("\r\n") for line in f if line.strip()]

    def _write(self, name: str, lines: list[str]) -> None:
        p = self.path(name)
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write("".join(line + "\n" for line in lines))
        os.replace(tmp, p)

    def count(self, name: str) -> int:
        with self._lock:
            return len(self._read(name))

    def peek(self, name: str, n: int = 10) -> list[str]:
        with self._lock:
            return self._read(name)[:n]

    def take(self, name: str, n: int) -> list[str] | None:
        """Снимает ``n`` первых строк. ``None``, если строк меньше ``n``."""
        with self._lock:
            lines = self._read(name)
            if len(lines) < n:
                return None
            self._write(name, lines[n:])
            return lines[:n]

    def give_back(self, name: str, items: list[str]) -> None:
        with self._lock:
            self._write(name, items + self._read(name))

    def add(self, name: str, items: list[str]) -> int:
        items = [i.strip() for i in items if i.strip()]
        with self._lock:
            self._write(name, self._read(name) + items)
            return len(items)

    def clear(self, name: str) -> None:
        with self._lock:
            self._write(name, [])


def unescape_item(item: str) -> str:
    return item.replace("\\n", "\n")
