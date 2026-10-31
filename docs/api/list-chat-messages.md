# list-chat-messages

GET/api/public/v1/chats/{chat}/messages
Право: chats:read
История чата
Пример200Пример4XX
Страница истории
 (56 строк)
Информация
Сообщения тем же видом, что на сайте у вас: скрытое сотрудником или ИИ отсутствует (номера с дырами), удалённое и стёртое без текста, «Только арбитру» собеседника и сообщение арбитра другой стороне приходят плашкой (withheld: true). Отметки «через API» в ответе нет.
Два режима, как пары «по созданию / updated_since» у /orders. Без after_seq: последние limit сообщений, next_cursor ведёт к более ранним. С after_seq: сообщения с номером больше, next_cursor ведёт дальше вперёд, на последней странице has_next_page: false. В обоих режимах items по возрастанию seq.
Схема бота: вебхук message.created, затем GET …/messages?after_seq=<последний известный>, ответ POST …/messages, по желанию POST …/read.
Право: chats:read.
Параметры
Путь
chatОбязательныйstring · uuid
Чат: id из GET /chats
Строка запроса
after_seqinteger · 0–2 147 483 647
Режим «вперёд»: сообщения с номером больше, по возрастанию. Без поля: последние, следующая страница более ранние
cursorstring · до 255 знаков
next_cursor предыдущей страницы того же режима; мусор и курсор другого режима: первая страница режима
limitinteger · 1–100 · по умолчанию 50
Сообщений на странице


## Примеры

```
{
  "data": {
    "items": [
      {
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
      {
        "id": "0199e0a5-4b3c-7d2e-8f10-2a3b4c5d6e7f",
        "seq": 8,
        "type": "text",
        "author": "me",
        "staff_role": null,
        "text": "Выдал, проверьте",
        "images": [],
        "attachments": [],
        "reply_to": {
          "id": "0199e0a3-1d2e-7a40-9b51-6c7d8e9f0a1b",
          "seq": 7
        },
        "automatic": false,
        "edited_at": null,
        "deleted": false,
        "redacted": false,
        "withheld": false,
        "visibility": "all",
        "system": null,
        "read_by_counterpart": false,
        "client_message_id": "5a3c0d8e-2f1b-4c6d-9e8f-7a6b5c4d3e2f",
        "created_at": "2026-10-30T09:21:10+00:00"
      }
    ],
    "has_next_page": true,
    "next_cursor": "Ynw3",
    "last_read_seq": 7,
    "counterpart_last_read_seq": 7
  },
  "status": true
}
```

```
curl https://api.izi.market/api/public/v1/chats/0199e0a1-7c2b-7f10-8a11-3c4d5e6f7a8b/messages \
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
    "message": "Диалог не найден",
    "code": "conversation_not_found"
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
      "limit": [
        "Значение поля размер страницы не может быть больше 100."
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
