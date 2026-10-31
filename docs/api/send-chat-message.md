# send-chat-message

POST/api/public/v1/chats/{chat}/messages
Право: chats:writeИзменяющийIdempotency-Key
Ответить в чат
Пример201Пример4XX
Сообщение отправлено
Информация
Отправка тем же сценарием, что на сайте, от вашего имени: те же стоп-фразы, правило ссылок, срез своих рекламных меток, чёрный список, «5 сообщений до ответа» в личном диалоге, окно 72 часа после закрытия заказа, картинки; собеседник получает сообщение в реальном времени, непрочитанное, письмо, пуш и копию в Telegram, ИИ-модерация проверяет его, как любое. Только в существующий чат, где вы сторона: начать диалог, написать «Только арбитру», приложить товар, править и удалять через API нельзя.
Повтор: Idempotency-Key (ответ первого запроса сутки) и client_message_id (как на сайте, навсегда). Свой вебхук message.created ваш ответ вам не даёт.
Лимиты сверх окон продавца: общий с сайтом 30 сообщений в минуту и 2000 в сутки на аккаунт и 10 в минуту и 200 в сутки на один чат. Отказ лимита места в окнах продавца не тратит.
В журнале запросов текст и картинки под маской. Право: chats:write. Заблокированный владелец ключа через API не пишет никуда.
Параметры
Путь
chatОбязательныйstring · uuid
Чат: id из GET /chats
Заголовки
Idempotency-Keystring
Ключ повтора: 8–120 знаков — латиница, цифры, - и _; свой у продавца, живёт сутки. Тот же запрос с тем же ключом получает ответ первого и заголовок Idempotent-Replayed: true; другой запрос с тем же ключом — 409 public_api_idempotency_conflict; первый ещё выполняется — 409 public_api_idempotency_in_progress. Отказ ключ не занимает.
Шаблон:^[A-Za-z0-9_-]{8,120}$
Тело запроса · JSON
textstring · до 4 000 знаков
Текст; без images обязателен. По метке U+FFFC на каждую картинку. Ссылка разметкой [подпись](https://адрес) по правилам сайта
imagesмассив string · до 10 элементов · без повторов
id загрузок POST /chats/media по порядку меток. Только в чате заказа и при включённых картинках чатов
reply_to_idstring или null · uuid
Ответ на сообщение этого чата: над ответом будет цитата
client_message_idstring · uuid
Ваш ключ сообщения: повтор с ним вернёт прежнее, другое содержимое под ним даст 409 message_idempotency_conflict. Без поля ключ выдаёт сервер


## Примеры

```
curl https://api.izi.market/api/public/v1/chats/0199e0a1-7c2b-7f10-8a11-3c4d5e6f7a8b/messages \
  -X POST \
  -H 'Authorization: Bearer izp_…' \
  -H 'Accept: application/json' \
  -H 'Idempotency-Key: f47ac10b-58cc-4372-a567-0e02b2c3d479' \
  -H 'Content-Type: application/json' \
  -d '{
    "text": "Выдал, проверьте",
    "reply_to_id": "0199e0a3-1d2e-7a40-9b51-6c7d8e9f0a1b",
    "client_message_id": "5a3c0d8e-2f1b-4c6d-9e8f-7a6b5c4d3e2f"
}'
```

```
{
  "data": {
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
    "message": "Вы заблокировали этого пользователя",
    "code": "user_blocked"
  },
  "status": false
}
```

```
{
  "data": {
    "message": "Пользователь ограничил общение с вами",
    "code": "blocked_by_user"
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
    "message": "Загрузка не найдена",
    "code": "upload_not_found"
  },
  "status": false
}
```

```
{
  "data": {
    "message": "Переписка по этой сделке закрыта: писать в неё больше нельзя",
    "code": "conversation_read_only"
  },
  "status": false
}
```

```
{
  "data": {
    "message": "Дождитесь ответа собеседника, прежде чем писать дальше",
    "code": "direct_reply_awaited"
  },
  "status": false
}
```

```
{
  "data": {
    "message": "Картинки в этой переписке не принимаются",
    "code": "chat_images_not_allowed"
  },
  "status": false
}
```

```
{
  "data": {
    "message": "Этот ключ сообщения уже использован для другого текста",
    "code": "message_idempotency_conflict"
  },
  "status": false
}
```

```
{
  "data": {
    "message": "Загрузка уже привязана к другому объекту",
    "code": "upload_already_claimed"
  },
  "status": false
}
```

```
{
  "data": {
    "message": "Этот ключ повтора уже использован с другим запросом — для нового запроса нужен новый ключ",
    "code": "public_api_idempotency_conflict"
  },
  "status": false
}
```

```
{
  "data": {
    "message": "Запрос с этим ключом повтора ещё выполняется — повторите через секунду",
    "code": "public_api_idempotency_in_progress",
    "retry_after": 1
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
      "audience": [
        "Приватные сообщения через API не отправляются"
      ]
    }
  },
  "status": false
}
```

```
{
  "data": {
    "message": "Текст содержит запрещённую фразу: «telegram» — уберите её",
    "code": "stop_phrase_found",
    "field": "description",
    "errors": {
      "description": [
        "Текст содержит запрещённую фразу: «telegram» — уберите её"
      ]
    }
  },
  "status": false
}
```

```
{
  "data": {
    "message": "Загрузка сделана с другим назначением",
    "code": "upload_kind_mismatch"
  },
  "status": false
}
```

```
{
  "data": {
    "message": "Ключ повтора Idempotency-Key — от 8 до 120 знаков: латиница, цифры, «-» и «_»",
    "code": "public_api_idempotency_key_invalid"
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
