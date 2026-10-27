# upload-image

POST/api/public/v1/media
Право: products:writeИзменяющийIdempotency-Key
Загрузить картинку
Информация
Картинка товара: multipart/form-data, поле file, до 10 МБ, JPEG, PNG или WebP. Назначение одно — картинка товара: поле kind не читается. id ответа уходит в images создания и images.add правки; загрузка, которую не забрал товар, исчезает в expires_at. status: pending — уменьшенные копии ещё собираются, товар с такой картинкой выставлять можно. Принимает Idempotency-Key.
Право — products:write.
Параметры
Заголовки
Idempotency-Keystring
Ключ повтора: 8–120 знаков — латиница, цифры, - и _; свой у продавца, живёт сутки. Тот же запрос с тем же ключом получает ответ первого и заголовок Idempotent-Replayed: true; другой запрос с тем же ключом — 409 public_api_idempotency_conflict; первый ещё выполняется — 409 public_api_idempotency_in_progress. Отказ ключ не занимает.
Шаблон:^[A-Za-z0-9_-]{8,120}$
Тело запроса · multipart/form-data
fileОбязательныйфайл
Картинка: JPEG, PNG или WebP, до 10 МБ



## 201: Загрузка принята
```json
{
  "data": {
    "id": "6ca24316-da69-4635-bf2c-ac133b5d00e0",
    "status": "pending",
    "expires_at": "2026-10-15T12:00:00+00:00",
    "url": "/storage/product_image/2026/10/5b28fb7a-83f6-413f-9349-50662f48545a/original.png",
    "mime": "image/png",
    "width": 640,
    "height": 480,
    "size_bytes": 993
  },
  "status": true
}
```

Ошибки: 401:public_api_key_invalid | 403:account_blocked,account_email_required,account_email_unverified,public_api_scope_missing | 409:public_api_idempotency_conflict,public_api_idempotency_in_progress | 422:animated_image_not_allowed,image_too_large,image_too_many_pixels,public_api_idempotency_key_invalid,unsupported_image,validation_failed | 429:too_many_requests,upload_quota_exceeded | 503:site_maintenance,storage_unavailable