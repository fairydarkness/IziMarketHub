# mark-chat-read

POST/api/public/v1/chats/{chat}/read
Право: chats:writeИзменяющий
Отметить прочитанным
Пример200Пример4XX
Отметка прочтения
Информация
Прочитано до seq или, без него, всё, что есть в чате сейчас. Отметка только растёт и не уходит дальше последнего сообщения. Последствия те же, что на сайте: собеседник видит «прочитано», ваши вкладки гасят счётчик, отложенные письма и копии в Telegram о сообщениях до отметки не уходят. Сама отправка тоже ставит вашу отметку на ваше сообщение.
Право: chats:write.
Параметры
Путь
chatОбязательныйstring · uuid
Чат: id из GET /chats
Тело запроса · JSON
seqinteger · 0–2 147 483 647
Прочитано до этого номера включительно; без поля: всё, что есть в чате сейчас


## Примеры

```
curl https://api.izi.market/api/public/v1/chats/0199e0a1-7c2b-7f10-8a11-3c4d5e6f7a8b/read \
  -X POST \
  -H 'Authorization: Bearer izp_…' \
  -H 'Accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "seq": 7
}'
```

```
{
  "data": {
    "last_read_seq": 7,
    "unread_count": 0
  },
  "status": true
}
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
      "seq": [
        "Значение поля номер должно быть не меньше 0."
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
