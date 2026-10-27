# get-image

GET/api/public/v1/media/{upload}
Право: products:write
Загрузка
Информация
Своя загрузка в той же форме, что ответ загрузки, — например, чтобы дождаться status: ready. Чужая и несуществующая — 404 upload_not_found.
Право — products:write.
Параметры
Путь
uploadОбязательныйstring · uuid
Загрузка — id из POST /media



## 200: Загрузка
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

Ошибки: 401:public_api_key_invalid | 403:account_blocked,account_email_required,account_email_unverified,public_api_scope_missing | 404:upload_not_found | 429:too_many_requests | 503:site_maintenance