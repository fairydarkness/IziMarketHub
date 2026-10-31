# upload-chat-image

POST/api/public/v1/chats/media
Право: chats:writeИзменяющийIdempotency-Key
Загрузить картинку чата
Пример201Пример4XX
Загрузка принята
Информация
Картинка для ответа в чат заказа: та же загрузка, что у переписки на сайте. Файл ложится на приватный диск, адрес подписан и живёт минуты; квота своя, картинок переписки (100 загрузок и 200 МБ за скользящие сутки), квоту фото товаров не тратит. id уходит в images отправки; незабранная загрузка исчезает в expires_at. Картинка товара из POST /media в чат не забирается.
Картинки чатов выключены на площадке: 409 chat_images_not_allowed до загрузки.
Право: chats:write.
Параметры
Заголовки
Idempotency-Keystring
Ключ повтора: 8–120 знаков — латиница, цифры, - и _; свой у продавца, живёт сутки. Тот же запрос с тем же ключом получает ответ первого и заголовок Idempotent-Replayed: true; другой запрос с тем же ключом — 409 public_api_idempotency_conflict; первый ещё выполняется — 409 public_api_idempotency_in_progress. Отказ ключ не занимает.
Шаблон:^[A-Za-z0-9_-]{8,120}$
Тело запроса · multipart/form-data
fileОбязательныйфайл
Картинка: JPEG, PNG или WebP, до 10 МБ


## Примеры

```
curl https://api.izi.market/api/public/v1/chats/media \
  -X POST \
  -H 'Authorization: Bearer izp_…' \
  -H 'Accept: application/json' \
  -H 'Idempotency-Key: f47ac10b-58cc-4372-a567-0e02b2c3d479' \
  -F 'file=@image.png'
```

```
{
  "data": {
    "id": "0199e0b0-5a6b-7c8d-9e0f-1a2b3c4d5e6f",
    "status": "pending",
    "expires_at": "2026-10-31T09:20:00+00:00",
    "url": "https://cdn.izi.market/private/chat_image/2026/10/0199e0b0/original.png?signature=…",
    "mime": "image/png",
    "width": 1280,
    "height": 720,
    "size_bytes": 184320
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
    "message": "Картинки в этой переписке не принимаются",
    "code": "chat_images_not_allowed"
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
      "file": [
        "Поле файл обязательно."
      ]
    }
  },
  "status": false
}
```

```
{
  "data": {
    "message": "Файл не является изображением поддерживаемого формата",
    "code": "unsupported_image"
  },
  "status": false
}
```

```
{
  "data": {
    "message": "Файл больше допустимого размера",
    "code": "image_too_large"
  },
  "status": false
}
```

```
{
  "data": {
    "message": "Изображение слишком большое по количеству точек",
    "code": "image_too_many_pixels"
  },
  "status": false
}
```

```
{
  "data": {
    "message": "Анимированные картинки в фото товара не принимаются — загрузите неподвижное изображение",
    "code": "animated_image_not_allowed"
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
    "message": "Исчерпан суточный предел загрузок, попробуйте позже",
    "code": "upload_quota_exceeded",
    "exceeded": "uploads",
    "limit": {
      "uploads": 200,
      "bytes": 524288000
    },
    "used": {
      "uploads": 200,
      "bytes": 318767104
    },
    "window_seconds": 86400,
    "retry_at": "2026-10-23T09:41:07+00:00",
    "retry_after": 5321
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

```
{
  "data": {
    "message": "Хранилище файлов временно недоступно, попробуйте ещё раз",
    "code": "storage_unavailable"
  },
  "status": false
}
```
