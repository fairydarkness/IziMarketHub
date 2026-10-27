# get-subcategory-schema

GET/api/public/v1/catalog/subcategories/{subcategory}/schema
Право: catalog:read
Схема подкатегории
Информация
Что подкатегория потребует от товара: границы цены и количества (settings) и поля. Поля source: seller — значения товара: уходят в attrs формы по key; у списка значение — id опции, у мультивыбора — список id. Поля source: delivery — поля единицы склада. visible_if и hidden_if — условия показа и скрытия, скрытие сильнее; скрытое поле не обязательно, и его значение не сохраняется. settings.verified_sellers_only — выставить сюда может только верифицированный продавец, settings.premoderation — товар сначала увидит модератор.
Ответ кешируйте: он приходит с ETag, повтор с If-None-Match того же значения — 304 без тела. ETag меняется и со схемой полей, и с премодерацией подкатегории; ответ разный на разных языках (Vary: Accept-Language).
Право — catalog:read.
Параметры
Путь
subcategoryОбязательныйinteger · ≥ 1
Подкатегория — id из GET /catalog/tree
Заголовки
If-None-Matchstring
ETag прошлого ответа



## 200: Схема подкатегории
```json
{
  "data": {
    "version": "19862dd5e8943bd5309d",
    "subcategory": {
      "id": 3,
      "slug": "mail",
      "name": "Почты",
      "type": "stock",
      "unit_name": null,
      "category": {
        "id": 1,
        "slug": "roblox",
        "name": "Roblox"
      }
    },
    "settings": {
      "min_price_minor": 100,
      "max_price_minor": 100000000000,
      "min_listing_quantity": 1,
      "max_listing_quantity": 100000,
      "min_order_quantity": 1,
      "max_order_quantity": 1000,
      "verified_sellers_only": false,
      "premoderation": true
    },
    "fields": [
      {
        "key": "protocol_mail_service",
        "label": "Протоколы",
        "hint": null,
        "type": "multiselect",
        "source": "seller",
        "required": true,
        "rules": {},
        "unit": null,
        "visible_if": null,
        "hidden_if": null,
        "group_axis": false,
        "options": [
          {
            "id": 1,
            "slug": "imap",
            "label": "IMAP",
            "group": null,
            "custom": false
          },
          {
            "id": 2,
            "slug": "pop3",
            "label": "POP3",
            "group": null,
            "custom": false
          },
          {
            "id": 3,
            "slug": "web",
            "label": "WEB",
            "group": null,
            "custom": false
          }
        ]
      },
      {
        "key": "logpass",
        "label": "Логин:пароль",
        "hint": null,
        "type": "text",
        "source": "delivery",
        "required": true,
        "rules": {},
        "unit": null,
        "visible_if": null,
        "hidden_if": null,
        "group_axis": false,
        "options": []
      },
      {
        "key": "web_mail",
        "label": "Ссылка на веб-интерфейс",
        "hint": null,
        "type": "text",
        "source": "delivery",
        "required": true,
        "rules": {},
        "unit": null,
        "visible_if": {
          "field": "protocol_mail_service",
          "op": "in",
          "value": [
            "web"
          ]
        },
        "hidden_if": null,
        "group_axis": false,
        "options": []
      }
    ]
  },
  "status": true
}
```

Ошибки: 304: | 401:public_api_key_invalid | 403:account_blocked,account_email_required,account_email_unverified,public_api_scope_missing | 404:subcategory_not_found | 429:too_many_requests | 503:site_maintenance