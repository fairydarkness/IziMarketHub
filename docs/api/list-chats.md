# list-chats

GET/api/public/v1/chats
Право: chats:read
Список чатов
Пример200Пример4XX
Страница чатов
 (51 строка)
Информация
Ваши личные диалоги и чаты заказов, где вы сторона, от свежих к старым по last_message_at, курсором, как GET /orders. Обращений в поддержку и чата с собой здесь нет никогда. Видимость как на сайте: чат заказа, в котором ещё не было живого слова, продавцу виден только при type=order; личный диалог, скрытый сотрудником целиком, отсутствует. Закрепа нет: закреплённые на сайте идут в общем порядке.
Чат заказа заводит покупка, поэтому сразу после order.created поиск по order_id может несколько секунд быть пустым. Начать диалог через API нельзя.
Право: chats:read. Ключам, выпущенным без явного выбора этого права, оно не достаётся.
Параметры
Строка запроса
typestring · по умолчанию all
Вид: direct, order или all (по умолчанию)
Значения:directorderall
unread_onlyboolean
Только с непрочитанным: 1, true
order_idstring · uuid
Чат этого заказа, если вы его сторона и чат уже заведён: один элемент или пусто, курсор не читается
cursorstring · до 255 знаков
next_cursor предыдущей страницы того же запроса; мусор: первая страница
limitinteger · 1–50 · по умолчанию 20
Чатов на странице


## Примеры

```
{
  "data": {
    "items": [
      {
        "id": "0199e0a1-7c2b-7f10-8a11-3c4d5e6f7a8b",
        "type": "order",
        "created_at": "2026-10-30T09:12:44+00:00",
        "counterpart": {
          "id": "6f0b1c2d-3e4f-4a5b-8c6d-7e8f9a0b1c2d",
          "number": 18342,
          "username": "kiwi_buyer",
          "verified_seller": false
        },
        "order": {
          "id": "0199d8c1-2c55-7d01-9a3e-7f1b2c3d4e5f",
          "title": "Robux 800",
          "role": "seller"
        },
        "last_seq": 7,
        "last_read_seq": 5,
        "counterpart_last_read_seq": 6,
        "unread_count": 2,
        "last_message": {
          "id": "0199e0a3-1d2e-7a40-9b51-6c7d8e9f0a1b",
          "seq": 7,
          "type": "text",
          "author": "counterpart",
          "staff_role": null,
          "text": "Здравствуйте, когда будет выдача?",
          "images": [],
          "attachments": [],
          "reply_to": null,
          "automatic": false,
          "edited_at": null,
          "deleted": false,
          "redacted": false,
          "withheld": false,
          "visibility": "all",
          "system": null,
          "read_by_counterpart": null,
          "client_message_id": null,
          "created_at": "2026-10-30T09:20:01+00:00"
        },
        "last_message_at": "2026-10-30T09:20:01+00:00"
      }
    ],
    "has_next_page": true,
    "next_cursor": "MjAyNi0xMC0zMFQwOToyMDowMSswMDowMHwwMTk5ZTBhMS03YzJiLTdmMTAtOGExMS0zYzRkNWU2ZjdhOGI="
  },
  "status": true
}
```

```
curl https://api.izi.market/api/public/v1/chats \
  -H 'Authorization: Bearer izp_…' \
  -H 'Accept: application/json'
```

```
{
  "data": {
    "message": "Нужен действующий ключ публичного API",
    "code": "public_api_key_invalid"
  },
  "status": false
}
```

```
{
  "data": {
    "message": "У ключа нет права «catalog:read» — выпустите ключ с этим правом",
    "code": "public_api_scope_missing",
    "scope": "catalog:read"
  },
  "status": false
}
```

```
{
  "data": {
    "message": "Аккаунт заблокирован. Обратитесь в поддержку",
    "code": "account_blocked",
    "reason": null,
    "ends_at": null
  },
  "status": false
}
```

```
{
  "data": {
    "message": "Укажите адрес почты и подтвердите его — до этого действия недоступны",
    "code": "account_email_required",
    "account_status": "restricted"
  },
  "status": false
}
```

```
{
  "data": {
    "message": "Подтвердите адрес почты — до этого действия недоступны",
    "code": "account_email_unverified",
    "account_status": "restricted"
  },
  "status": false
}
```

```
{
  "data": {
    "message": "Проверьте правильность заполнения полей",
    "code": "validation_failed",
    "errors": {
      "type": [
        "Значение поля вид отсутствует в списке разрешённых."
      ]
    }
  },
  "status": false
}
```

```
{
  "data": {
    "message": "Слишком много запросов, попробуйте позже",
    "code": "too_many_requests"
  },
  "status": false
}
```

```
{
  "data": {
    "message": "Идут технические работы — скоро вернёмся",
    "code": "site_maintenance",
    "return_at": "2026-10-14T13:00:00+00:00"
  },
  "status": false
}
```
