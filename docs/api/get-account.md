# get-account

GET/api/public/v1/account
Право: account:read
Аккаунт продавца
Информация
Владелец ключа — то, что видно на его публичной странице: имя, подпись, аватар, сколько товаров в продаже (stats.products) и завершённых продаж (stats.sales), рейтинг по отзывам. id — тот же, что user_id в GET /me и seller_id в вебхуках.
Почты, двухфакторной защиты, ролей, прав и санкций в ответе нет.
Право — account:read.



## 200: Публичный профиль владельца
```json
{
  "data": {
    "id": "01a13c13-f52d-732e-96df-618fbc9ad6da",
    "number": 1,
    "username": "kiwi_shop",
    "custom_title": "Ключи Steam за минуту",
    "registered_at": "2026-10-14T12:00:00+00:00",
    "avatar": null,
    "stats": {
      "products": 0,
      "sales": 0
    },
    "rating": {
      "average": null,
      "reviews_count": 0
    }
  },
  "status": true
}
```

Ошибки: 401:public_api_key_invalid | 403:account_blocked,account_email_required,account_email_unverified,public_api_scope_missing | 429:too_many_requests | 503:site_maintenance