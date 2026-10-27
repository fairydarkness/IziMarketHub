# bulk-update-products

POST/api/public/v1/products/bulk-update
Право: products:writeИзменяющий
Цена и количество пакетом
Информация
Цена, количество и свой минимум к покупке до 100 своих товаров одним вызовом: у каждого id, version и хотя бы одно из price_minor, quantity, min_order_quantity. Каждый товар правится отдельно, своей транзакцией, тем же путём, что PATCH: отказ одного не мешает другим и приходит в results[].error тем же code, что дал бы PATCH (stale_version, price_out_of_range, quantity_managed_by_stock, min_order_quantity_not_supported, product_not_found, validation_failed с errors). Ответ всегда 200, итог — по каждому товару в порядке запроса; results[].product — объект списка, сохраните новую version.
В окне записи пакет весит ⌈n / 10⌉: 100 товаров — 10 мест из 60.
Пакет не атомарен. Сбой посреди пакета (5xx, обрыв связи) оставляет часть товаров изменёнными. Повтор того же пакета безопасен: изменённые ответят stale_version.
Право — products:write.
Параметры
Тело запроса · JSON
itemsОбязательныймассив object · от 1 до 100 элементов
—



## 200: Итог по каждому товару
```json
{
  "data": {
    "updated": 1,
    "failed": 2,
    "results": [
      {
        "id": "0e330f41-c01d-47f0-b54f-d71e69c35111",
        "ok": true,
        "product": {
          "id": "0e330f41-c01d-47f0-b54f-d71e69c35111",
          "title": "Золото Roblox, 1000 шт., моментально",
          "status": "pending",
          "version": 6,
          "price": {
            "amount_minor": 82000,
            "currency": "RUB"
          },
          "quantity": 450,
          "low_stock_threshold": null,
          "min_order_quantity": null,
          "subcategory_id": 1,
          "deleted": false,
          "sales": 0,
          "auto_delivery": false,
          "delivery_mode": "manual",
          "shop": {
            "open": true,
            "opens_at": null,
            "closes_at": null,
            "closed_until": null
          },
          "stock_managed": false,
          "effective_min_order_quantity": 1,
          "needs_update": false,
          "rejection_reason": null,
          "published_at": "2026-10-14T12:00:00+00:00",
          "pricing_mode": "deduct",
          "commission": {
            "amount_minor": 8200,
            "currency": "RUB"
          },
          "seller_receives": {
            "amount_minor": 73800,
            "currency": "RUB"
          },
          "cost": {
            "amount_minor": 30000,
            "currency": "RUB"
          },
          "profit_per_unit": {
            "amount_minor": 43800,
            "currency": "RUB"
          },
          "group_id": null
        }
      },
      {
        "id": "7b04c4c3-f1a5-42f8-b55e-c207b6df5715",
        "ok": false,
        "error": {
          "message": "Количество лота с автовыдачей считает склад: добавьте или уберите единицы",
          "code": "quantity_managed_by_stock"
        }
      },
      {
        "id": "0e6937ea-77cc-4fff-8e5e-3df1fa173296",
        "ok": false,
        "error": {
          "message": "Товар не найден",
          "code": "product_not_found"
        }
      }
    ]
  },
  "status": true
}
```

Ошибки: 401:public_api_key_invalid | 403:account_blocked,account_email_required,account_email_unverified,public_api_scope_missing | 422:validation_failed | 429:too_many_requests | 503:site_maintenance