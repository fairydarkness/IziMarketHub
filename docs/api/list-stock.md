# list-stock

GET/api/public/v1/products/{product}/stock
Право: stock:read
Склад товара
Информация
Склад товара автовыдачи, свежие первыми. Свободная единица — целиком (content, fields), выданная и заменённая — под маской. available — свободных единиц, это же quantity товара; sold — выдано сделкам вместе с заменёнными в споре.
Параметры — только из строки запроса: JSON-тело у GET не читается. q ищет по свободным единицам без учёта регистра и только с status=available; q — часть товара и оседает в журналах доступа серверов по дороге.
Право — stock:read.
Параметры
Путь
productОбязательныйstring · uuid
Товар — id из GET /products
Строка запроса
statusstring
Только единицы в этом статусе
Значения:availablesoldreplaced
pageinteger · ≥ 1 · по умолчанию 1
Страница
per_pageinteger · 1–200 · по умолчанию 50
Единиц на странице
qstring · до 200 знаков
Поиск по свободным единицам; только с status=available



## 200: Страница склада
```json
{
  "data": {
    "items": [
      {
        "id": 3,
        "status": "available",
        "content": "HADES-7Q2M-K4PX-0003",
        "fields": null,
        "order_id": null,
        "created_at": "2026-10-14T12:00:00+00:00",
        "sold_at": null
      },
      {
        "id": 2,
        "status": "available",
        "content": "HADES-7Q2M-K4PX-0002",
        "fields": null,
        "order_id": null,
        "created_at": "2026-10-14T12:00:00+00:00",
        "sold_at": null
      },
      {
        "id": 1,
        "status": "sold",
        "content": "HA••••01",
        "fields": null,
        "order_id": "5f43fbfd-9e0b-4910-8b41-3a23b74abaa7",
        "created_at": "2026-10-14T12:00:00+00:00",
        "sold_at": "2026-10-14T12:06:00+00:00"
      }
    ],
    "has_next_page": false,
    "available": 2,
    "sold": 1,
    "matched": null
  },
  "status": true
}
```

Ошибки: 401:public_api_key_invalid | 403:account_blocked,account_email_required,account_email_unverified,public_api_scope_missing | 404:product_not_found | 422:validation_failed | 429:too_many_requests | 503:site_maintenance