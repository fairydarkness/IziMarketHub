# create-product-group

POST/api/public/v1/products/groups
Право: products:writeИзменяющийIdempotency-Key
Склеить товары
Информация
Склейка своих товаров одной подкатегории, которые различаются значением одного поля — оси (срок, регион): на витрине группа — одна карточка, на странице товара — переключатель. Цена, склад, модерация и сделка остаются у каждого товара; версия и статус товаров не меняются. Ось — поле схемы подкатегории с group_axis: true (GET /catalog/subcategories/{subcategory}/schema).
От 2 до 50 своих товаров, у каждого — своё значение оси. Товар в любом состоянии, кроме удалённого.
Право — products:write.
Параметры
Заголовки
Idempotency-Keystring
Ключ повтора: 8–120 знаков — латиница, цифры, - и _; свой у продавца, живёт сутки. Тот же запрос с тем же ключом получает ответ первого и заголовок Idempotent-Replayed: true; другой запрос с тем же ключом — 409 public_api_idempotency_conflict; первый ещё выполняется — 409 public_api_idempotency_in_progress. Отказ ключ не занимает.
Шаблон:^[A-Za-z0-9_-]{8,120}$
Тело запроса · JSON
product_idsОбязательныймассив string · от 2 до 50 элементов · без повторов
Свои товары одной подкатегории с разными значениями оси; у замены — весь новый состав



## 201: Группа: ось и товары в порядке опций оси
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

Ошибки: 401:public_api_key_invalid | 403:account_blocked,account_email_required,account_email_unverified,public_api_scope_missing | 404:product_not_found | 409:product_already_grouped,public_api_idempotency_conflict,public_api_idempotency_in_progress | 422:product_group_axis_missing,product_group_axis_taken,product_group_axis_value_missing,product_group_mixed,public_api_idempotency_key_invalid,validation_failed | 429:too_many_requests | 503:site_maintenance