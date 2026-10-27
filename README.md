# IziMarketHub

## [VPN](https://t.me/fairyvpn_bot) 

Если проект полезен - поставь ⭐  
Связаться / отблагодарить - Telegram [@fairydarkns](https://t.me/fairydarkns)

Бот продавца для [IziMarket](https://izi.market): автовыдача, автодеактивация лотов, пополнение склада
и управление магазином из Telegram. Работает через официальное
[публичное API продавца](https://izi.market/settings/api/docs).

**Автор:** [@fairydarkns](https://t.me/fairydarkns)

## Возможности

**Продажи**
- **Автовыдача.** Новая оплаченная сделка выдаётся сразу: товар берётся из `.txt` файла, текст строится по шаблону с переменными.
- **Поля выдачи.** Если подкатегория требует поля (логин, пароль…), строка `kiwi:melon` раскладывается по ним.
- **Автодеактивация.** Когда файл товара опустел, лот снимается с продажи.
- **Автовосстановление.** Когда в файле снова появились строки, лот выставляется обратно.
- **Пополнение склада площадки.** Для товаров со складом автовыдачи IziMarket бот докладывает единицы из файла, когда свободных остаётся мало.
- **Синхронизация количества** (по желанию). Количество лота приводится к числу строк в файле.
- **Выдача пропущенного.** Сделки, оплаченные пока бот был выключен, выдаются при запуске.

**Telegram**
- Уведомления о новых сделках, выдаче, спорах, завершении и возвратах, о снятии лотов и пополнении склада.
- Ручная выдача сделки прямо из уведомления.
- Настройка автовыдачи: привязать товар, сменить текст, включить или выключить, добавить строки в файл текстом или `.txt`.
- Мои товары: снять с продажи или выставить, поменять цену и количество.
- Баланс с деньгами в холде по продажам, последние сделки, статистика за 7 дней, файл логов.
- Обновление из GitHub командой `/update` и перезапуск `/restart`.
- Несколько чатов, у каждого свой набор уведомлений. Вход по паролю.

**Прочее**
- Плагины без правки кода (`plugins/`).
- Вебхуки с проверкой подписи. Они ускоряют реакцию, но не обязательны: бот опрашивает API.
- `IziAPI/` — отдельный клиент API, можно использовать в своих скриптах.

> В публичном API нет чата и поднятия лотов, поэтому автоответчика и автоподнятия, как у FunPay-ботов, здесь нет.

## Установка

Нужен Python 3.11+.

```bash
git clone https://github.com/fairydarkness/IziMarketHub && cd IziMarketHub
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python main.py --setup   # ключ API, Telegram, пароль
.venv/bin/python main.py
```

Или запустите `./start.sh`: он сам создаст окружение и при первом запуске откроет настройку.

### Ключ API

На izi.market откройте **Настройки → API → Ключи → Выпустить**. Нужные права:

| Право | Зачем |
|---|---|
| `orders:read`, `orders:write` | видеть и выдавать сделки |
| `products:read`, `products:write` | снимать и выставлять лоты, менять цену и количество |
| `stock:read`, `stock:write` | пополнять склад автовыдачи |
| `balance:read`, `analytics:read` | баланс и статистика в Telegram |

Ключи, выпущенные до 20.10.2026, не умеют выдавать сделки: для этого нужен новый ключ.
Ключ можно не хранить в конфиге, а передать переменной окружения `IZI_API_KEY`.

## Автовыдача

Настраивается в `configs/auto_delivery.cfg` или через Telegram (**📦 Автовыдача → ➕ Привязать товар**).

```ini
# имя секции — id товара из ссылки https://izi.market/products/<id> или точное название
[7b04c4c3-f1a5-42f8-b55e-c207b6df5715]
response = Спасибо за покупку, $username!\nВаш ключ:\n$product
productsFileName = hades.txt

[Аккаунт Steam]
response = Данные от аккаунта ниже. Смените пароль после входа.
productsFileName = steam.txt
fields = login,password
```

Файлы товаров лежат в `storage/products/`. Одна строка — одна единица товара, перенос строки внутри товара записывается как `\n`.
Если куплено несколько штук, выдаётся столько же строк.

| Параметр | Значение |
|---|---|
| `response` | текст выдачи (по умолчанию `$product`) |
| `productsFileName` | файл товара |
| `fields` | ключи полей выдачи подкатегории через запятую |
| `disable` | `1` — не выдавать автоматически |
| `disableAutoDisable` | `1` — не снимать лот, когда файл пуст |
| `disableAutoRestore` | `1` — не выставлять лот обратно |
| `stockRefill` | `1` — для товара со складом площадки докладывать строки на склад (по умолчанию включено) |

**Переменные:** `$username`, `$product`, `$product_title`, `$product_id`, `$order_id`, `$quantity`,
`$amount`, `$seller_amount`, `$date`, `$time`, `$input_<ключ>` (то, что ввёл покупатель, например `$input_nick`),
`$param_<N>` (выбранный параметр по номеру группы).

### Товары со складом площадки

Если у товара включена автовыдача со склада IziMarket (`delivery_mode = stock`), сделку выдаёт сама площадка, и бот её не трогает.
Если товар привязан к файлу, бот при остатке на складе не больше `[StockRefill] threshold` переносит туда до `batch` строк из файла.
Строки, которые площадка отклонила, и пачки без ответа сервера складываются в `storage/refill_failed/`. В основной файл они не возвращаются, чтобы один товар не продали дважды.

## Надёжность выдачи

- Сделки опрашиваются по `updated_since` с запасом в минуту (раз в `pollInterval` секунд), повторы отсеиваются по статусу. Так сделка не теряется и не выдаётся дважды.
- Строки снимаются с файла до выдачи. Если площадка отказала (сделка уже выдана, отменена…), строки возвращаются в файл.
- Если ответа нет, бот перечитывает сделку. Если узнать исход не удалось, строки в файл не возвращаются, а в Telegram приходит предупреждение с этими строками: проверьте сделку вручную.
- Учитываются лимиты API (300 запросов в минуту, 60 изменяющих) и `Retry-After`.

## Вебхуки (по желанию)

1. На izi.market: **Настройки → API → Webhooks** — выпустите ключ подписи `izs_…`.
2. В `configs/_main.cfg` включите `[Webhook] enabled = 1` и задайте `signingSecret`.
3. IziMarket шлёт вебхуки только на `https://` с публичным адресом. Пробросьте `127.0.0.1:8080/izimarket` через nginx, Caddy или туннель и укажите этот адрес в кабинете.

Вебхук только будит бота: данные всё равно берутся из API, поэтому пропущенный вебхук ничего не ломает.

## Конфиг `configs/_main.cfg`

```ini
[IziMarket]
apiKey = izp_…
locale = ru
pollInterval = 15          ; секунд между опросами сделок
autoDelivery = 1
autoDisable = 1
autoRestore = 1
stockRefill = 1
syncQuantity = 0
deliverPendingOnStart = 1
proxy =

[StockRefill]
checkInterval = 300
threshold = 5
batch = 50

[Telegram]
enabled = 1
token = …
secretKeyHash = …          ; создаётся в --setup
proxy =

[Webhook]
enabled = 0
host = 127.0.0.1
port = 8080
path = /izimarket
signingSecret =

[Other]
debug = 0
```

## Плагины

Плагин — это `.py` файл в `plugins/`. Его можно положить в папку руками или отправить боту (**🧩 Плагины → ➕ Добавить**).
Пример лежит в `plugins/_example_plugin.py`: файлы, чьё имя начинается с `_`, не загружаются.

```python
NAME = "Мой плагин"
VERSION = "1.0"
DESCRIPTION = "…"
CREDITS = "@you"
UUID = "сгенерируйте uuid4"

def on_new_order(hub, order):
    hub.tg.notify("new_order", f"Ещё одна продажа: {order.product_title}")

BIND_TO_NEW_ORDER = [on_new_order]
```

События: `PRE_INIT`, `POST_INIT`, `PRE_START`, `POST_START`, `PRE_STOP`, `NEW_ORDER`, `ORDER_STATUS_CHANGED`,
`ORDER_DELIVERED`, `DELIVERY_FAILED`, `PRODUCT_DISABLED`, `PRODUCT_RESTORED`, `STOCK_REFILLED`, `WEBHOOK_EVENT`.
Аргументы событий перечислены в `hub.py`. Внутри плагина доступны `hub.client` (весь API), `hub.goods`, `hub.store`, `hub.tg`.

⚠️ Плагин получает полный доступ к компьютеру и ключу API. Ставьте только проверенные.

## Обновление

В Telegram: `/update` или **меню → стр. 2 → 🔄 Обновление**. Бот покажет новые коммиты, а по кнопке
выполнит `git pull`, доставит зависимости, если изменился `requirements.txt`, и перезапустится.
`configs/`, `storage/` и `logs/` при этом не затрагиваются.

Обновление работает, только если бот установлен через `git clone`. Если файлы бота правились вручную,
бот откажется обновляться и покажет, какие файлы мешают. В Docker обновляйте так: `git pull && docker compose up -d --build`.

Вручную на сервере:
```bash
cd IziMarketHub && git pull && .venv/bin/pip install -r requirements.txt
```

## Запуск 24/7

**systemd:**
```bash
sudo cp IziMarketHub@.service /etc/systemd/system/
sudo systemctl enable --now IziMarketHub@$USER
```
Сервис ожидает проект в `~/IziMarketHub`. Если он лежит в другом месте, поправьте `WorkingDirectory`.

**Docker:**
```bash
docker compose run --rm imh python main.py --setup
docker compose up -d
```

## Структура

```
IziAPI/          клиент публичного API IziMarket (отдельный пакет)
tg_bot/          Telegram-бот
Utils/           конфиги, хранилище, шаблоны, логи
plugins/         плагины
configs/         _main.cfg, auto_delivery.cfg
storage/         products/*.txt, cache/state.json
docs/api/        копия документации API
hub.py           ядро: опрос, события, плагины
handlers.py      автовыдача, деактивация, пополнение склада
webhook_server.py
main.py
```

Тесты: `.venv/bin/pip install pytest && .venv/bin/python -m pytest tests`
