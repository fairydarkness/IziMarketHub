# replace-product-group

PUT/api/public/v1/products/groups/{group}
Право: products:writeИзменяющий
Новый состав группы
Информация
Весь новый состав, а не добавка: товары вне списка выходят из группы. Правила те же, что у создания; товары самой группы product_already_grouped не получают, товар другой подкатегории — 422 product_group_mixed.
Право — products:write.
Параметры
Путь
groupОбязательныйstring · uuid
Группа — id из ответа POST /products/groups
Тело запроса · JSON
product_idsОбязательныймассив string · от 2 до 50 элементов · без повторов
Свои товары одной подкатегории с разными значениями оси; у замены — весь новый состав



## 200: Группа после замены
```json
{
  "data": {
    "id": "7a1f2c3d-4b5e-4f60-8a71-92b3c4d5e6f7",
    "subcategory_id": 12,
    "axis": {
      "key": "duration",
      "name": "Срок"
    },
    "products": [
      {
        "id": "0e330f41-c01d-47f0-b54f-d71e69c35111",
        "title": "Чит для Rust, приватный",
        "status": "active",
        "value": 41,
        "value_label": "24 часа"
      },
      {
        "id": "3c9d1e52-7a40-4b8f-9e61-0d2f3a4b5c6d",
        "title": "Чит для Rust, приватный",
        "status": "active",
        "value": 42,
        "value_label": "7 дней"
      }
    ],
    "created_at": "2026-10-21T18:04:11+00:00"
  },
  "status": true
}
```

Ошибки: 401:public_api_key_invalid | 403:account_blocked,account_email_required,account_email_unverified,public_api_scope_missing | 404:product_group_not_found,product_not_found | 409:product_already_grouped | 422:product_group_axis_missing,product_group_axis_taken,product_group_axis_value_missing,product_group_mixed,validation_failed | 429:too_many_requests | 503:site_maintenance