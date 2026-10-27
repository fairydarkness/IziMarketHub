# get-catalog-tree

GET/api/public/v1/catalog/tree
Право: catalog:read
Дерево каталога
Информация
Открытые категории и их открытые подкатегории — куда можно выставить товар. id подкатегории уходит в subcategory_id формы товара, её требования — GET /catalog/subcategories/{subcategory}/schema.
type — механика сделки: unique — уникальный товар, stock — со склада, currency — валюта, service — услуга (количество — сколько заказов продавец готов взять, покупают по одному). unit_name — единица валюты. Названия — на языке Accept-Language.
Право — catalog:read.



## 200: Дерево каталога
```json
{
  "data": {
    "items": [
      {
        "id": 1,
        "slug": "roblox",
        "name": "Roblox",
        "subcategories": [
          {
            "id": 1,
            "slug": "gold",
            "name": "Золото",
            "type": "currency",
            "unit_name": "шт."
          },
          {
            "id": 2,
            "slug": "items",
            "name": "Предметы",
            "type": "stock",
            "unit_name": null
          },
          {
            "id": 3,
            "slug": "mail",
            "name": "Почты",
            "type": "stock",
            "unit_name": null
          }
        ]
      }
    ]
  },
  "status": true
}
```

Ошибки: 401:public_api_key_invalid | 403:account_blocked,account_email_required,account_email_unverified,public_api_scope_missing | 429:too_many_requests | 503:site_maintenance