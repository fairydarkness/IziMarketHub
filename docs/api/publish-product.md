# publish-product

POST/api/public/v1/products/{product}/publish
Право: products:writeИзменяющий
Отправить товар
Информация
Отправить черновик или снятый товар: дальше он у модератора либо сразу в продаже — по правилам подкатегории. Снятый и не правленный товар возвращается в продажу сразу. Тело не нужно; locale — язык основного текста, если его надо назвать.
У черновика без картинки или без названия на языке сайта — 422 validation_failed: дополните товар PATCH и повторите.
Право — products:write.
Параметры
Путь
productОбязательныйstring · uuid
Товар — id из GET /products
Тело запроса · JSON
localestring или null
Значения:ruen



## 200: Товар после отправки
```json
{
  "data": {
    "id": "0e330f41-c01d-47f0-b54f-d71e69c35111",
    "title": "Золото Roblox, 1000 шт., моментально",
    "status": "pending",
    "version": 5,
    "price": {
      "amount_minor": 81000,
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
      "amount_minor": 8100,
      "currency": "RUB"
    },
    "seller_receives": {
      "amount_minor": 72900,
      "currency": "RUB"
    },
    "cost": {
      "amount_minor": 30000,
      "currency": "RUB"
    },
    "profit_per_unit": {
      "amount_minor": 42900,
      "currency": "RUB"
    },
    "group_id": null,
    "listed_price": {
      "amount_minor": 81000,
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
    "parameters": [],
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

Ошибки: 401:public_api_key_invalid | 403:account_blocked,account_email_required,account_email_unverified,public_api_scope_missing,seller_not_verified | 404:product_not_found | 409:product_state_invalid,stale_version | 422:price_below_minimum_commission,price_out_of_range,subcategory_not_available,validation_failed | 429:too_many_requests | 503:site_maintenance