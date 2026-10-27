"""IziMarketHub — бот продавца IziMarket. Автор: @fairydarkns (https://t.me/fairydarkns)."""

from __future__ import annotations

import argparse
import logging
import os
import sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from Utils.config_loader import MAIN_CFG, ConfigError, load_auto_delivery_config, load_main_config  # noqa: E402
from Utils.logger import setup_logging  # noqa: E402

LOGO = r"""
  ___     _ __  __            _        _   _  _       _
 |_ _|___(_)  \/  | __ _ _ __| | _____| |_| || |_   _| |__
  | ||_  / | |\/| |/ _` | '__| |/ / _ \ __| __ | | | | '_ \
  | | / /| | |  | | (_| | |  |   <  __/ |_| || | |_| | |_) |
 |___/___|_|_|  |_|\__,_|_|  |_|\_\___|\__|_||_|\__,_|_.__/
                                         by @fairydarkns
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="IziMarketHub — бот продавца IziMarket")
    parser.add_argument("--setup", action="store_true", help="первичная настройка")
    args = parser.parse_args()

    if args.setup or not os.path.exists(MAIN_CFG):
        from first_setup import run_setup
        run_setup()
        if args.setup:
            return

    print(LOGO)
    try:
        main_cfg = load_main_config()
        ad_cfg = load_auto_delivery_config()
    except ConfigError as e:
        sys.exit(f"Ошибка конфига: {e}")

    setup_logging(main_cfg.getboolean("Other", "debug"))
    log = logging.getLogger("IMH")

    from handlers import register_handlers
    from hub import IziMarketHub

    hub = IziMarketHub(main_cfg, ad_cfg)
    # уведомления — первыми, чтобы «новая сделка» приходила раньше «выдана»
    if main_cfg.getboolean("Telegram", "enabled"):
        from tg_bot.bot import TGBot
        hub.tg = TGBot(hub)
        hub.tg.bind()
    register_handlers(hub)

    hub.load_plugins()
    hub.init()
    log.info(f"Автовыдача настроена для {len(ad_cfg.sections())} товаров")

    webhook = None
    if main_cfg.getboolean("Webhook", "enabled"):
        from webhook_server import WebhookServer
        webhook = WebhookServer(hub)
        webhook.start()

    if hub.tg:
        hub.tg.start()
    try:
        hub.run()
    finally:
        if webhook:
            webhook.stop()


if __name__ == "__main__":
    main()
