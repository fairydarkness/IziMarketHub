# get-order

GET/api/public/v1/orders/{order}
Право: orders:read
Сделка
Информация
Своя продажа — тот же объект, что элемент списка. Сделки нет, это покупка владельца ключа или чужая сделка — ответ один и тот же, 404 order_not_found.
Право — orders:read.
Параметры
Путь
orderОбязательныйstring · uuid
Сделка — id из GET /orders



## 200: Сделка
```json
{
  "data": {
    "id": "01a13c13-f761-7231-92ec-6f80c06ee40b",
    "status": "completed",
    "product_id": "01a13c13-f761-7231-92ec-6f80bf741643",
    "quantity": 1,
    "amount": {
      "amount_minor": 79000,
      "currency": "RUB"
    },
    "commission": {
      "amount_minor": 7900,
      "currency": "RUB"
    },
    "seller_amount": {
      "amount_minor": 71100,
      "currency": "RUB"
    },
    "created_at": "2026-10-14T12:00:00+00:00",
    "deliver_due_at": "2026-10-14T12:00:00+00:00",
    "delivered_at": "2026-10-13T12:01:00+00:00",
    "confirm_due_at": "2026-10-16T12:00:00+00:00",
    "closed_at": "2026-10-13T14:00:00+00:00",
    "payout_due_at": "2026-10-16T12:00:00+00:00",
    "paid_out_at": null,
    "updated_at": "2026-10-14T12:00:00+00:00",
    "product_title": "Robux 800",
    "payout_held": false,
    "cost": {
      "amount_minor": 30000,
      "currency": "RUB"
    },
    "profit": {
      "amount_minor": 41100,
      "currency": "RUB"
    },
    "buyer": {
      "id": "01a13c13-f75e-73af-8412-954ed993bbf7",
      "username": "kiwi_buyer",
      "inputs": {
        "nick": "kiwi_in_game"
      },
      "parameters": [
        {
          "group_id": 12,
          "type": "radio",
          "title_ru": "Регион",
          "title_en": "Region",
          "options": [
            {
              "option_id": 32,
              "label_ru": "Глобальный",
              "label_en": "Global",
              "price_delta_minor": 0
            }
          ],
          "value": null
        },
        {
          "group_id": 13,
          "type": "text",
          "title_ru": "ID игрока",
          "title_en": "Player ID",
          "options": [],
          "value": "700100200"
        }
      ]
    }
  },
  "status": true
}
```

Ошибки: 401:public_api_key_invalid | 403:account_blocked,account_email_required,account_email_unverified,public_api_scope_missing | 404:order_not_found | 429:too_many_requests | 503:site_maintenance