# update-product

PATCH/api/public/v1/products/{product}
Право: products:writeИзменяющий
Изменить товар
Информация
Правка: присланные поля меняются, остальные — нет. Поля — как у создания, плюс обязательная version — версия, которую видел скрипт; товар изменился после чтения — 409 stale_version: перечитайте товар и повторите с новой version. Картинки — объектом {"keep": [<images[].id>], "add": [<id загрузок>], "order": [...]}. Цену и количество продаваемого товара можно менять без модератора. parameters — набор целиком: свои группы и варианты называются своим id; изменённый набор уходит на модерацию, как правка названия, а набор, где поменялись только надбавки, — нет: это правка цены.
Ответ — товар после правки, version — следующая.
Право — products:write.
Параметры
Путь
productОбязательныйstring · uuid
Товар — id из GET /products
Тело запроса · JSON
versionОбязательныйinteger · ≥ 1
Версия товара, которую видел скрипт
titlestring · от 3 до 160 знаков
—
descriptionstring или null · до 8 000 знаков
—
description_docobject или null
Документ редактора; задан — description не нужен
translationsobject или null
Название на каждом языке сайта, кроме основного; кроме черновика
localestring или null
Язык основного текста; нет — язык Accept-Language
Значения:ruen
price_minorinteger · 0–100 000 000 000
Цена в копейках рубля, которую называет продавец; у склада и валюты — цена единицы
pricing_modestring
Значения:deductmarkup
cost_minorinteger или null · ≥ 0
Себестоимость единицы; видна только продавцу
quantityinteger · 1–100 000
Сколько единиц, в границах схемы; у услуги — сколько заказов продавец готов взять
min_order_quantityinteger или null · 1–100 000
Свой минимум к покупке, правила те же, что у создания; null снимает. Не правка содержания: version не растёт, модерации нет. Переезд в подкатегорию unique или service снимает минимум сам
subcategory_idinteger · ≥ 1
—
attrsobject
Значения полей source: seller схемы по key; у варианта custom — ещё своё значение в <key>__custom
parametersмассив object или null · до 10 элементов
Параметры лота целиком: присланный список заменяет прежний. Своя группа и свой вариант называются своим id и сохраняют его, без id — заводятся, неназванные — удаляются; чужой id — 422 по parameters.N.id. null и [] снимают все параметры, отсутствие ключа их не трогает. Изменённый набор — правка содержания: version растёт, лот уходит на модерацию по правилам подкатегории; поменялись только надбавки — правка цены: version растёт, лот остаётся в продаже; тот же набор — не правка
imagesobject
—



## 200: Товар после правки
```json
{
  "data": {
    "id": "0e330f41-c01d-47f0-b54f-d71e69c35111",
    "title": "Золото Roblox, 1000 шт., моментально",
    "status": "pending",
    "version": 2,
    "price": {
      "amount_minor": 79000,
      "currency": "RUB"
    },
    "quantity": 500,
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
      "amount_minor": 7900,
      "currency": "RUB"
    },
    "seller_receives": {
      "amount_minor": 71100,
      "currency": "RUB"
    },
    "cost": {
      "amount_minor": 30000,
      "currency": "RUB"
    },
    "profit_per_unit": {
      "amount_minor": 41100,
      "currency": "RUB"
    },
    "group_id": null,
    "listed_price": {
      "amount_minor": 79000,
      "currency": "RUB"
    },
    "description": "Передача трейдом в течение часа.",
    "description_doc": {
      "type": "doc",
      "content": [
        {
          "type": "paragraph",
          "content": [
            {
              "text": "Передача трейдом в течение часа.",
              "type": "text"
            }
          ]
        }
      ]
    },
    "locale": null,
    "translations": {
      "en": {
        "title": "Roblox gold, 1000 pcs",
        "description": null,
        "description_doc": null
      }
    },
    "subcategory": {
      "id": 1,
      "slug": "gold",
      "name": "Золото",
      "type": "currency",
      "unit_name": "шт.",
      "category": {
        "id": 1,
        "slug": "roblox",
        "name": "Roblox"
      }
    },
    "attrs": {},
    "parameters": [],
    "images": [
      {
        "id": "5b28fb7a-83f6-413f-9349-50662f48545a",
        "url": "/storage/product_image/2026/10/5b28fb7a-83f6-413f-9349-50662f48545a/original.png",
        "width": 640,
        "height": 480,
        "status": "pending"
      }
    ],
    "hidden_by_verification": false,
    "url": "https://izi.market/products/0e330f41-c01d-47f0-b54f-d71e69c35111"
  },
  "status": true
}
```

Ошибки: 401:public_api_key_invalid | 403:account_blocked,account_email_required,account_email_unverified,public_api_scope_missing,seller_not_verified | 404:product_not_found | 409:stale_version | 422:image_not_available,min_order_quantity_not_supported,price_below_minimum_commission,price_out_of_range,quantity_managed_by_stock,stop_phrase_found,subcategory_not_available,too_many_images,validation_failed | 429:too_many_requests | 503:site_maintenance