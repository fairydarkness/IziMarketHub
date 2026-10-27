# list-products

GET/api/public/v1/products
Право: products:read
Список товаров
Информация
Свои товары во всех состояниях, по 40 на страницу; без sort — свежие первыми. Общего числа нет намеренно — листайте, пока has_next_page. Первые десять ключей товара — объект product вебхуков, ключ в ключ: ответ и вебхук разбираются одним кодом.
Единиц склада, настройки и содержимого выдачи в ответе нет ни в каком виде.
Право — products:read.
Параметры
Строка запроса
pageinteger · 1–50 000 · по умолчанию 1
Номер страницы, с 1
statusstring
Только товары в этом состоянии
Значения:draftpendingactiverejectedhidden
gamestring · до 100 знаков
Только товары этой игры — адрес категории каталога (roblox)
Шаблон:^[a-z0-9-]+$
searchstring · до 100 знаков
Поиск по названию
sortstring · по умолчанию fresh
Порядок
Значения:fresholdestprice_descprice_ascsalesstock



## 200: Страница товаров
```json
{
  "data": {
    "items": [
      {
        "id": "0e330f41-c01d-47f0-b54f-d71e69c35111",
        "title": "Золото Roblox, 1000 шт., моментально",
        "status": "pending",
        "version": 6,
        "price": {
          "amount_minor": 82000,
          "currency": "RUB"
        },
        "quantity": 450,
        "low_stock_threshold": null,
        "min_order_quantity": null,
        "subcategory_id": 1,
        "deleted": false,
        "sales": 0,
        "auto_delivery": false,
        "delivery_mode": "manual",
        "shop": {
          "open": true,
          "opens_at": null,
          "closes_at": null,
          "closed_until": null
        },
        "stock_managed": false,
        "effective_min_order_quantity": 1,
        "needs_update": false,
        "rejection_reason": null,
        "published_at": "2026-10-14T12:00:00+00:00",
        "pricing_mode": "deduct",
        "commission": {
          "amount_minor": 8200,
          "currency": "RUB"
        },
        "seller_receives": {
          "amount_minor": 73800,
          "currency": "RUB"
        },
        "cost": {
          "amount_minor": 30000,
          "currency": "RUB"
        },
        "profit_per_unit": {
          "amount_minor": 43800,
          "currency": "RUB"
        },
        "group_id": null
      },
      {
        "id": "7b04c4c3-f1a5-42f8-b55e-c207b6df5715",
        "title": "Ключ Hades, Steam",
        "status": "active",
        "version": 4,
        "price": {
          "amount_minor": 49000,
          "currency": "RUB"
        },
        "quantity": 1,
        "low_stock_threshold": null,
        "min_order_quantity": null,
        "subcategory_id": 2,
        "deleted": false,
        "sales": 0,
        "auto_delivery": true,
        "delivery_mode": "stock",
        "shop": null,
        "stock_managed": true,
        "effective_min_order_quantity": 1,
        "needs_update": false,
        "rejection_reason": null,
        "published_at": "2026-10-14T12:00:00+00:00",
        "pricing_mode": "deduct",
        "commission": {
          "amount_minor": 4900,
          "currency": "RUB"
        },
        "seller_receives": {
          "amount_minor": 44100,
          "currency": "RUB"
        },
        "cost": null,
        "profit_per_unit": null,
        "group_id": null
      }
    ],
    "has_next_page": false,
    "current_page": 1
  },
  "status": true
}
```

Ошибки: 401:public_api_key_invalid | 403:account_blocked,account_email_required,account_email_unverified,public_api_scope_missing | 422:validation_failed | 429:too_many_requests | 503:site_maintenance