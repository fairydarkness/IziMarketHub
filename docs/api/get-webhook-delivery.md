# get-webhook-delivery

GET/api/public/v1/webhook/deliveries/{delivery}
Право: webhooks
Доставка
Информация
Доставка, событие целиком — тот же конверт {id, type, api_version, occurred_at, data}, что получил приёмник, — и все попытки с кодом и началом тела ответа.
Право — webhooks.
Параметры
Путь
deliveryОбязательныйstring · uuid
Доставка — id из GET /webhook/deliveries



## 200: Доставка, событие и попытки
```json
{
  "data": {
    "delivery": {
      "id": "01a13c13-f7cc-735e-b02d-8192d8970e70",
      "event_id": "01a13c13-f7cc-735e-b02d-8192d9515a15",
      "type": "product.stock.depleted",
      "status": "delivered",
      "attempts": 2,
      "url": "https://hooks.kiwi-shop.example/izimarket",
      "occurred_at": "2026-10-14T12:00:00+00:00",
      "created_at": "2026-10-14T12:00:00+00:00",
      "last_attempt_at": "2026-10-14T12:01:01+00:00",
      "next_attempt_at": null,
      "delivered_at": "2026-10-14T12:01:01+00:00",
      "last_attempt": {
        "response_status": 200,
        "duration_ms": 35,
        "failure": null,
        "outcome": null,
        "created_at": "2026-10-14T12:01:01+00:00"
      }
    },
    "event": {
      "id": "01a13c13-f7cc-735e-b02d-8192d9515a15",
      "type": "product.stock.depleted",
      "api_version": "2026-10",
      "occurred_at": "2026-10-14T12:00:00+00:00",
      "data": {
        "product": {
          "id": "01a13c13-f7c9-7144-a887-14d5b1e54c28",
          "title": "Robux 800",
          "status": "active",
          "version": 2,
          "price": {
            "amount_minor": 79000,
            "currency": "RUB"
          },
          "quantity": 0,
          "low_stock_threshold": null,
          "min_order_quantity": null,
          "subcategory_id": null,
          "deleted": false
        },
        "change": {
          "before": 1,
          "after": 0,
          "low_stock_threshold": null,
          "min_order_quantity": null,
          "cause": "order",
          "order_id": null
        }
      }
    },
    "attempts": [
      {
        "attempt": 1,
        "url": "https://hooks.kiwi-shop.example/izimarket",
        "response_status": 503,
        "duration_ms": 40,
        "failure": null,
        "response_body": "busy",
        "outcome": null,
        "created_at": "2026-10-14T12:00:00+00:00"
      },
      {
        "attempt": 2,
        "url": "https://hooks.kiwi-shop.example/izimarket",
        "response_status": 200,
        "duration_ms": 35,
        "failure": null,
        "response_body": "ok",
        "outcome": null,
        "created_at": "2026-10-14T12:01:01+00:00"
      }
    ]
  },
  "status": true
}
```

Ошибки: 401:public_api_key_invalid | 403:account_blocked,account_email_required,account_email_unverified,public_api_scope_missing | 404:webhook_delivery_not_found | 429:too_many_requests | 503:site_maintenance