# add-product-variant

POST/api/public/v1/products/{product}/variants
Право: products:writeИзменяющийIdempotency-Key
Добавить вариант
Информация
Вариант — близнец товара со своим значением оси (срок, регион), ценой и количеством: название, описание, переводы, поля и картинки — товара. Вариант встаёт в группу товара (собирает её, если группы не было), и покупатель видит одну карточку с переключателем. Вариант одобренного товара сразу в продаже, ждущего — ждёт вместе с ним, черновика — черновик. Склад и настройка выдачи у варианта свои. Параметры товара вариант получает копией со своими id — они в parameters ответа; с ценой варианта самый дешёвый или самый дорогой выбор вне границ раздела — 422 validation_failed по price_minor.
Право — products:write.
Параметры
Путь
productОбязательныйstring · uuid
Товар — id из GET /products
Заголовки
Idempotency-Keystring
Ключ повтора: 8–120 знаков — латиница, цифры, - и _; свой у продавца, живёт сутки. Тот же запрос с тем же ключом получает ответ первого и заголовок Idempotent-Replayed: true; другой запрос с тем же ключом — 409 public_api_idempotency_conflict; первый ещё выполняется — 409 public_api_idempotency_in_progress. Отказ ключ не занимает.
Шаблон:^[A-Za-z0-9_-]{8,120}$
Тело запроса · JSON
valueОбязательныйinteger
Значение оси — id опции поля с group_axis: true схемы подкатегории; у каждого варианта группы своё
price_minorОбязательныйinteger · ≥ 0
Цена варианта в копейках; что она значит, решает pricing_mode товара
quantityОбязательныйinteger · ≥ 1
—
cost_minorinteger или null · ≥ 0
Себестоимость единицы варианта
min_order_quantityinteger или null · ≥ 1
Свой минимум к покупке; только у валюты и склада



## 201: Новый вариант — объект товара; он уже в группе товара (`group_id`)
```json
{
  "data": {
    "id": "0e330f41-c01d-47f0-b54f-d71e69c35111",
    "title": "Золото Roblox, 1000 шт., моментально",
    "status": "active",
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
    "group_id": "7a1f2c3d-4b5e-4f60-8a71-92b3c4d5e6f7",
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

Ошибки: 401:public_api_key_invalid | 403:account_blocked,account_email_required,account_email_unverified,public_api_scope_missing | 404:product_not_found | 409:product_state_invalid,public_api_idempotency_conflict,public_api_idempotency_in_progress | 422:min_order_quantity_not_supported,price_below_minimum_commission,price_out_of_range,product_group_axis_missing,product_group_axis_taken,product_group_axis_value_missing,public_api_idempotency_key_invalid | 429:too_many_requests | 503:site_maintenance