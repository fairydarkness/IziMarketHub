# delete-product

DELETE/api/public/v1/products/{product}
Право: products:writeИзменяющий
Удалить товар
Информация
Удалить товар: 204 без тела. Товар пропадает из списка и с витрины, сделки по нему идут своим путём. Повтор — 404 product_not_found.
Право — products:write.
Параметры
Путь
productОбязательныйstring · uuid
Товар — id из GET /products



## 204: Товар удалён

Ошибки: 401:public_api_key_invalid | 403:account_blocked,account_email_required,account_email_unverified,public_api_scope_missing | 404:product_not_found | 429:too_many_requests | 503:site_maintenance