# get-chat

GET/api/public/v1/chats/{chat}
Право: chats:read
Карточка чата
Пример200Пример4XX
Чат
 (49 строк)
Информация
Элемент списка и признаки записи: можно ли писать и почему нет (write_blocked_reason: код, которым ответила бы отправка), можно ли приложить картинку (images_blocked_reason). Личный диалог, скрытый сотрудником, по прямому адресу есть, но без скрытого, как на сайте.
Право: chats:read.
Параметры
Путь
chatОбязательныйstring · uuid
Чат: id из GET /chats


## Примеры

```
{
  "data": {
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
    "last_message_at": "2026-10-30T09:20:01+00:00",
    "can_write": true,
    "write_blocked_reason": null,
    "can_send_images": false,
    "images_blocked_reason": "chat_images_not_allowed"
  },
  "status": true
}
```

```
curl https://api.izi.market/api/public/v1/chats/0199e0a1-7c2b-7f10-8a11-3c4d5e6f7a8b \
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
