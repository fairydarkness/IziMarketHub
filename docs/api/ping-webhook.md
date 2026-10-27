# ping-webhook

POST/api/public/v1/webhook/ping
Право: webhooksИзменяющий
Проверить ссылку
Информация
Отправляет на ссылку событие ping тем же путём и с той же подписью, что настоящие события, и ждёт ответа приёмника (до 10 секунд). Выключенная ссылка ping тоже получает: это проверка. Ответ — 200 и при недоставке: исход доставки — данные (delivered, response_status, failure), а не отказ. В журнал доставок ping не попадает и не повторяется. Не больше 6 в минуту и 100 в сутки на продавца (суточное окно: 24 часа от первого ping), счётчик общий с кабинетом; отказ этих лимитов: 429 too_many_requests с Retry-After, места в окнах продавца он не тратит.
Право — webhooks.



## 200: Исход тестовой доставки
```json
{
  "data": {
    "event_id": "01a13c13-f7c3-709f-8188-3ea007fe60d1",
    "delivered": true,
    "response_status": 200,
    "duration_ms": 184,
    "failure": null,
    "response_body": "ok"
  },
  "status": true
}
```

Ошибки: 401:public_api_key_invalid | 403:account_blocked,account_email_required,account_email_unverified,public_api_scope_missing | 404:webhook_endpoint_not_found | 409:webhook_signing_key_missing | 429:too_many_requests | 503:site_maintenance