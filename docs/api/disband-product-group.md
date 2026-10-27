# disband-product-group

DELETE/api/public/v1/products/groups/{group}
Право: products:writeИзменяющий
Распустить группу
Информация
Роспуск: 204 без тела, товары остаются, каждый сам по себе. Группа распадается и сама: удалённый товар и товар, переехавший в другую подкатегорию, из неё выходят, а группа меньше двух товаров распускается.
Право — products:write.
Параметры
Путь
groupОбязательныйstring · uuid
Группа — id из ответа POST /products/groups



## 204: Группа распущена

Ошибки: 401:public_api_key_invalid | 403:account_blocked,account_email_required,account_email_unverified,public_api_scope_missing | 404:product_group_not_found | 429:too_many_requests | 503:site_maintenance