# redeliver-webhook-delivery

POST/api/public/v1/webhook/deliveries/{delivery}/redeliver
Право: webhooksИзменяющий
Отправить повторно
Информация
Отправляет событие ещё раз: новая доставка того же события на нынешнюю ссылку — то же тело и id события, новый X-IziMarket-Delivery-Id. Прежняя доставка остаётся в журнале как была. Повторить можно delivered, failed и dead. Ответ — 202, новая доставка в статусе pending. Не больше 30 повторов в минуту и 1000 в сутки на продавца (суточное окно: 24 часа от первого повтора), счётчик общий с кабинетом; отказ этих лимитов: 429 too_many_requests с Retry-After, места в окнах продавца он не тратит.
Право — webhooks.
Параметры
Путь
deliveryОбязательныйstring · uuid
Доставка — id из GET /webhook/deliveries



## 202: Новая доставка
```json
{
  "data": {
    "id": "01a13c13-f7e8-71ae-80d4-5fe3b3bb719a",
    "event_id": "01a13c13-f7cc-735e-b02d-8192d9515a15",
    "type": "product.stock.depleted",
    "status": "pending",
    "attempts": 0,
    "url": "https://hooks.kiwi-shop.example/izimarket",
    "occurred_at": "2026-10-14T12:00:00+00:00",
    "created_at": "2026-10-14T12:01:01+00:00",
    "last_attempt_at": null,
    "next_attempt_at": "2026-10-14T12:01:01+00:00",
    "delivered_at": null,
    "last_attempt": null
  },
  "status": true
}
```

Ошибки: 401:public_api_key_invalid | 403:account_blocked,account_email_required,account_email_unverified,public_api_scope_missing | 404:webhook_delivery_not_found,webhook_endpoint_not_found | 409:webhook_delivery_in_progress,webhook_endpoint_disabled | 429:too_many_requests | 503:site_maintenance