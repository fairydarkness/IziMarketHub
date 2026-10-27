# delete-stock-item

DELETE/api/public/v1/products/{product}/stock/{item}
Право: stock:writeИзменяющий
Удалить единицу склада
Информация
Удалить свободную единицу: 204 без тела. Количество товара убывает. Выданную удалить нельзя — 409 stock_item_not_available.
Право — stock:write.
Параметры
Путь
productОбязательныйstring · uuid
Товар — id из GET /products
itemОбязательныйinteger · ≥ 1
Единица склада — id из GET …/stock



## 204: Единица удалена

Ошибки: 401:public_api_key_invalid | 403:account_blocked,account_email_required,account_email_unverified,public_api_scope_missing | 404:product_not_found,stock_item_not_found | 409:stock_item_not_available | 429:too_many_requests | 503:site_maintenance