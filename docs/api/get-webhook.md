# get-webhook

GET/api/public/v1/webhook
Право: webhooks
Ссылка вебхука
Информация
Ссылка вебхука — одна на продавца: все типы событий идут на неё, приёмник различает их по type в теле или заголовку X-IziMarket-Event. events — фильтр типов, пусто — все. disabled_reason: failing — площадка выключила ссылку сама: та не приняла ни одного вебхука трое суток подряд; включить снова — PUT.
Право — webhooks.



## 200: Ссылка вебхука
```json
{
  "data": {
    "url": "https://hooks.kiwi-shop.example/izimarket",
    "events": [
      "product.stock.depleted",
      "order.created"
    ],
    "enabled": true,
    "disabled_reason": null,
    "failing_since": null,
    "created_at": "2026-10-14T12:00:00+00:00",
    "updated_at": "2026-10-14T12:00:00+00:00"
  },
  "status": true
}
```

Ошибки: 401:public_api_key_invalid | 403:account_blocked,account_email_required,account_email_unverified,public_api_scope_missing | 404:webhook_endpoint_not_found | 429:too_many_requests | 503:site_maintenance