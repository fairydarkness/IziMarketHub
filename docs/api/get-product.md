# get-product

GET/api/public/v1/products/{product}
Право: products:read
Товар
Информация
Свой товар целиком — объект элемента списка и после него поля правки: listed_price, тексты, подкатегория, attrs, картинки, hidden_by_verification, url. Форма та же, что у ответа записи: прочитал, поправил, отправил обратно.
Право — products:read.
Параметры
Путь
productОбязательныйstring · uuid
Товар — id из GET /products



## 200: Товар
```json
{
  "data": {
    "id": "0e330f41-c01d-47f0-b54f-d71e69c35111",
    "title": "Золото Roblox, 1000 шт.",
    "status": "active",
    "version": 1,
    "price": {
      "amount_minor": 79000,
      "currency": "RUB"
    },
    "quantity": 500,
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
      "amount_minor": 7900,
      "currency": "RUB"
    },
    "seller_receives": {
      "amount_minor": 71100,
      "currency": "RUB"
    },
    "cost": {
      "amount_minor": 30000,
      "currency": "RUB"
    },
    "profit_per_unit": {
      "amount_minor": 41100,
      "currency": "RUB"
    },
    "group_id": null,
    "listed_price": {
      "amount_minor": 79000,
      "currency": "RUB"
    },
    "description": "Передача трейдом в течение часа.",
    "description_doc": {
      "type": "doc",
      "content": [
        {
          "type": "paragraph",
          "content": [
            {
              "text": "Передача трейдом в течение часа.",
              "type": "text"
            }
          ]
        }
      ]
    },
    "locale": null,
    "translations": {
      "en": {
        "title": "Roblox gold, 1000 pcs",
        "description": null,
        "description_doc": null
      }
    },
    "subcategory": {
      "id": 1,
      "slug": "gold",
      "name": "Золото",
      "type": "currency",
      "unit_name": "шт.",
      "category": {
        "id": 1,
        "slug": "roblox",
        "name": "Roblox"
      }
    },
    "attrs": {},
    "parameters": [
      {
        "id": 12,
        "type": "radio",
        "title_ru": "Номинал",
        "title_en": "Amount",
        "required": true,
        "options": [
          {
            "id": 31,
            "label_ru": "1000 шт.",
            "label_en": "1000 pcs",
            "price_delta_minor": 0,
            "is_default": true,
            "hidden": false
          },
          {
            "id": 32,
            "label_ru": "5000 шт.",
            "label_en": "5000 pcs",
            "price_delta_minor": 316000,
            "is_default": false,
            "hidden": false
          }
        ]
      },
      {
        "id": 13,
        "type": "text",
        "title_ru": "Ник в игре",
        "title_en": "In-game nickname",
        "required": true,
        "options": []
      }
    ],
    "images": [
      {
        "id": "5b28fb7a-83f6-413f-9349-50662f48545a",
        "url": "/storage/product_image/2026/10/5b28fb7a-83f6-413f-9349-50662f48545a/original.png",
        "width": 640,
        "height": 480,
        "status": "pending"
      }
    ],
    "hidden_by_verification": false,
    "url": "https://izi.market/products/0e330f41-c01d-47f0-b54f-d71e69c35111"
  },
  "status": true
}
```

Ошибки: 401:public_api_key_invalid | 403:account_blocked,account_email_required,account_email_unverified,public_api_scope_missing | 404:product_not_found | 429:too_many_requests | 503:site_maintenance