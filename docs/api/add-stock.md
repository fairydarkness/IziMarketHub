# add-stock

POST/api/public/v1/products/{product}/stock
Право: stock:writeИзменяющийIdempotency-Key
Пополнить склад
Информация
Пополнить склад: до 1000 единиц за раз, тело до 8 МиБ. Единица — строкой ("login:password") либо объектом значений полей выдачи по key схемы; delimiter делит строку на поля. on_invalid: reject (по умолчанию) — плохая единица отвергает пачку целиком (422 stock_items_invalid, номера строк и поводы — в data.lines); skip — годные принимаются, прочие названы в rejected. Количество товара становится числом свободных единиц. Принимает Idempotency-Key.
Единицы — только из тела: присланное строкой запроса не читается — оно оседает в журналах доступа серверов по дороге. В журнале запросов единицы под маской, в вебхуки не попадают.
Право — stock:write.
Параметры
Путь
productОбязательныйstring · uuid
Товар — id из GET /products
Заголовки
Idempotency-Keystring
Ключ повтора: 8–120 знаков — латиница, цифры, - и _; свой у продавца, живёт сутки. Тот же запрос с тем же ключом получает ответ первого и заголовок Idempotent-Replayed: true; другой запрос с тем же ключом — 409 public_api_idempotency_conflict; первый ещё выполняется — 409 public_api_idempotency_in_progress. Отказ ключ не занимает.
Шаблон:^[A-Za-z0-9_-]{8,120}$
Тело запроса · JSON
itemsОбязательныймассив string | object · от 1 до 1 000 элементов
Единица — строкой либо объектом значений полей выдачи по key
delimiterstring или null · до 4 знаков · по умолчанию :
Разделитель полей в строке; табуляция — словом tab
on_invalidstring или null · по умолчанию reject
Значения:rejectskip



## 201: Склад пополнен
```json
{
  "data": {
    "added": 3,
    "available": 3,
    "rejected": [
      {
        "line": 4,
        "reason": "empty",
        "product_id": null
      }
    ]
  },
  "status": true
}
```

Ошибки: 401:public_api_key_invalid | 403:account_blocked,account_email_required,account_email_unverified,public_api_scope_missing | 404:product_not_found | 409:delivery_mode_conflict,public_api_idempotency_conflict,public_api_idempotency_in_progress | 422:public_api_idempotency_key_invalid,stock_items_invalid,stock_limit_exceeded,stock_not_supported,validation_failed | 429:too_many_requests | 503:site_maintenance