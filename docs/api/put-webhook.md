# put-webhook

PUT/api/public/v1/webhook
Право: webhooksИзменяющий
Задать ссылку вебхука
Информация
Форма целиком: присланное заменяет ссылку, не пришедшее поле берёт умолчание (events — все, enabled — true). Адрес — https, с именем хоста, без логина, пароля и #фрагмента; порт — 443 или от 1024 до 65535; все адреса имени должны быть публичными — это проверяется при сохранении и заново перед каждой доставкой. Вебхуки уходят через исходящий шлюз площадки — только по IPv4 и с его адреса (адреса шлюза — в кабинете, раздел «Webhooks»); имя с одними IPv6-адресами не доставить. PUT включает ссылку заново: disabled_reason и failing_since сбрасываются.
Сменить адрес можно не больше 10 раз в сутки (окно: 24 часа от первой смены, счётчик общий с кабинетом). Считается только новый адрес, в том числе первый, и только сохранённый; тот же адрес с другими events и enabled предел не тратит. Сверх предела ответ 429 webhook_url_change_limit, срок ожидания в data.retry_after и Retry-After.
Вебхуки подписывает ключ подписи продавца (izs_…), выпущенный в кабинете; без него вебхуки не уходят. Адрес шлюза общий для всех продавцов: белый список по адресу не доказывает, что запрос от площадки и для вас. Проверяйте подпись X-IziMarket-Signature.
Право — webhooks.
Параметры
Тело запроса · JSON
urlОбязательныйstring · до 2 048 знаков
https, с именем хоста, без логина и пароля и без #фрагмента; порт — 443 или от 1024 до 65535; адреса имени — публичные
eventsмассив string · без повторов
—
enabledboolean · по умолчанию true
—



## 200: Ссылка после правки
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

Ошибки: 401:public_api_key_invalid | 403:account_blocked,account_email_required,account_email_unverified,public_api_scope_missing | 422:validation_failed,webhook_url_not_public | 429:too_many_requests,webhook_url_change_limit | 503:site_maintenance