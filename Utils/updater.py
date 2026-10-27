"""Обновление IziMarketHub из GitHub через git и перезапуск процесса."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys

logger = logging.getLogger("IMH.update")

REPO_URL = "https://github.com/fairydarkness/IziMarketHub"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class UpdateError(Exception):
    pass


def _git(*args: str, timeout: int = 60) -> str:
    try:
        r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise UpdateError(f"git {args[0]}: нет ответа за {timeout} с") from None
    if r.returncode != 0:
        raise UpdateError(f"git {' '.join(args)}:\n{(r.stderr or r.stdout).strip()}")
    return r.stdout.strip()


def check_ready() -> None:
    if not shutil.which("git"):
        raise UpdateError("git не установлен")
    if not os.path.isdir(os.path.join(ROOT, ".git")):
        raise UpdateError(f"Папка бота — не git-репозиторий. Установите бота через git clone {REPO_URL}")


def pending_commits() -> list[str]:
    """Коммиты, которых ещё нет локально (после git fetch)."""
    check_ready()
    _git("fetch", "--quiet", "origin")
    try:
        _git("rev-parse", "--abbrev-ref", "@{u}")
    except UpdateError:
        raise UpdateError("У ветки нет upstream: выполните git branch --set-upstream-to=origin/main") from None
    log = _git("log", "--format=%h %s", "HEAD..@{u}")
    return [line for line in log.splitlines() if line]


def local_changes() -> list[str]:
    """Изменённые файлы под git. Файлы из .gitignore (configs, storage, logs) сюда не попадают."""
    out = _git("status", "--porcelain", "--untracked-files=no")
    return [line[3:] for line in out.splitlines() if line]


def update() -> list[str]:
    """git pull --ff-only; при смене requirements.txt — pip install. Возвращает новые коммиты."""
    commits = pending_commits()
    if not commits:
        return []
    changed = local_changes()
    if changed:
        raise UpdateError("Файлы бота изменены вручную, обновление их бы перезаписало:\n" + "\n".join(changed) +
                          "\n\nСохраните правки или откатите их: git checkout -- .")
    old = _git("rev-parse", "HEAD")
    _git("pull", "--ff-only", "--quiet", timeout=120)
    if "requirements.txt" in _git("diff", "--name-only", old, "HEAD").splitlines():
        logger.info("Обновились зависимости, ставлю…")
        r = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "requirements.txt"], cwd=ROOT,
                           capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            raise UpdateError(f"Код обновлён, но pip install упал:\n{r.stderr.strip()[-1500:]}")
    logger.info(f"Обновлено: {len(commits)} коммитов")
    return commits


def restart() -> None:
    """Перезапускает процесс тем же интерпретатором и с теми же аргументами."""
    logger.info("Перезапуск…")
    for h in logging.getLogger().handlers:
        h.flush()
    os.execv(sys.executable, [sys.executable, os.path.join(ROOT, "main.py"), *sys.argv[1:]])
