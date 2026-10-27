# get-me

GET/api/public/v1/me
Любой ключ
Чей это ключ
Информация
Проверка ключа программой продавца: чей он, какие у него права (key.scopes) и сколько он ещё проживёт (key.expires_at). Открыт ключу с любыми правами.
401 здесь не лечится повтором: истёкший или отозванный ключ не оживёт. Программа должна остановиться и попросить продавца выпустить новый ключ, а не повторять запрос в цикле.



## 200: Ключ и его владелец
```json
{
  "data": {
    "user_id": "01a13c13-f52d-732e-96df-618fbc9ad6da",
    "username": "kiwi_shop",
    "key": {
      "id": "d19f12d9-1980-4989-9338-bcc02fee49b6",
      "name": "Склад на сервере",
      "prefix": "izp_HEvQwuEE",
      "scopes": [
        "account:read",
        "balance:read",
        "products:read",
        "products:write",
        "stock:read",
        "stock:write",
        "catalog:read",
        "orders:read",
        "orders:write",
        "analytics:read",
        "webhooks"
      ],
      "expires_at": "2027-01-12T12:00:00+00:00",
      "expired": false,
      "last_used_at": "2026-10-14T12:00:00+00:00",
      "last_used_ip": "203.0.113.7",
      "created_at": "2026-10-14T12:00:00+00:00"
    }
  },
  "status": true
}
```

Ошибки: 401:public_api_key_invalid | 403:account_blocked,account_email_required,account_email_unverified | 429:too_many_requests | 503:site_maintenance