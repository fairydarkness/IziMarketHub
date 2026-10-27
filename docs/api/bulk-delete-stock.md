# bulk-delete-stock

POST/api/public/v1/products/{product}/stock/bulk-delete
Право: stock:writeИзменяющий
Удалить единицы пачкой
Информация
Удалить свободные единицы разом: {"ids": [...]} (до 1000) либо {"all": true}, с "q": "…" — только найденные. ids вместе с all или q — 422 validation_failed. Выбранные, но не удалённые — уже выданы, не этого товара или не подходят под q — считаются в skipped. Поля — только из тела.
Право — stock:write.
Параметры
Путь
productОбязательныйstring · uuid
Товар — id из GET /products
Тело запроса · JSON
idsмассив integer · от 1 до 1 000 элементов
—
allboolean
—
qstring или null · до 200 знаков
—



## 200: Итог удаления
```json
{
  "data": {
    "deleted": 1,
    "skipped": 1,
    "available": 1
  },
  "status": true
}
```

Ошибки: 401:public_api_key_invalid | 403:account_blocked,account_email_required,account_email_unverified,public_api_scope_missing | 404:product_not_found | 422:validation_failed | 429:too_many_requests | 503:site_maintenance