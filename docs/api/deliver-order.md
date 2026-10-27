# deliver-order

POST/api/public/v1/orders/{order}/deliver
Право: orders:writeИзменяющий
Выдать сделку
Информация
Отметить выдачу своей продажи — тем же сценарием, что «Я выполнил» на сайте: сделка из paid переходит в delivered, у покупателя идут срок подтверждения и окно спора, вам уходит вебхук order.delivered. Денег это не двигает. Выдача — content (текст: ключ, логин, ссылка, инструкция) и/или fields — значения полей выдачи по key схемы подкатегории, по которой сделку купили; у подкатегории с такими полями обязательные нужно заполнить, иначе 422 validation_failed с ключом fields.<key>. Пустая выдача (ни content, ни fields) — 422. Изменить выданное потом нельзя: замена — только в споре на сайте.
Сделки нет, это покупка владельца ключа или чужая сделка — 404 order_not_found, как у GET /orders/{order}. Сделка уже выдана, отменена или закрыта — 409 order_state_invalid с её статусом в data.current_status.
Выдача — только из тела: присланное строкой запроса не читается — оно оседает в журналах доступа серверов по дороге. В журнале запросов content и fields под маской.
Право — orders:write; чтение сделок его не даёт, и ключам, выпущенным до 20.10.2026, оно не достаётся — выпустите новый ключ.
Параметры
Путь
orderОбязательныйstring · uuid
Сделка — id из GET /orders
Тело запроса · JSON
contentstring или null · до 2 000 знаков
Чем передан товар: ключ, логин, ссылка, инструкция. Покупатель увидит это на странице сделки, арбитр — в споре. Без fields обязателен
fieldsobject или null
Значения полей выдачи по key схемы подкатегории; обязательные поля подкатегории нужно заполнить, лишние ключи отбрасываются. Без content обязателен



## 200: Сделка после выдачи
```json
{
  "data": {
    "id": "01a13c13-f761-7231-92ec-6f80c06ee40b",
    "status": "delivered",
    "product_id": "01a13c13-f761-7231-92ec-6f80bf741643",
    "quantity": 1,
    "amount": {
      "amount_minor": 79000,
      "currency": "RUB"
    },
    "commission": {
      "amount_minor": 7900,
      "currency": "RUB"
    },
    "seller_amount": {
      "amount_minor": 71100,
      "currency": "RUB"
    },
    "created_at": "2026-10-14T12:00:00+00:00",
    "deliver_due_at": "2026-10-15T12:00:00+00:00",
    "delivered_at": "2026-10-14T12:01:00+00:00",
    "confirm_due_at": "2026-10-17T12:01:00+00:00",
    "closed_at": null,
    "payout_due_at": null,
    "paid_out_at": null,
    "updated_at": "2026-10-14T12:01:00+00:00",
    "product_title": "Robux 800",
    "payout_held": false,
    "cost": {
      "amount_minor": 30000,
      "currency": "RUB"
    },
    "profit": {
      "amount_minor": 41100,
      "currency": "RUB"
    },
    "buyer": {
      "id": "01a13c13-f75e-73af-8412-954ed993bbf7",
      "username": "kiwi_buyer",
      "inputs": {
        "nick": "kiwi_in_game"
      },
      "parameters": [
        {
          "group_id": 12,
          "type": "radio",
          "title_ru": "Регион",
          "title_en": "Region",
          "options": [
            {
              "option_id": 32,
              "label_ru": "Глобальный",
              "label_en": "Global",
              "price_delta_minor": 0
            }
          ],
          "value": null
        },
        {
          "group_id": 13,
          "type": "text",
          "title_ru": "ID игрока",
          "title_en": "Player ID",
          "options": [],
          "value": "700100200"
        }
      ]
    }
  },
  "status": true
}
```

Ошибки: 401:public_api_key_invalid | 403:account_blocked,account_email_required,account_email_unverified,public_api_scope_missing | 404:order_not_found | 409:order_state_invalid | 422:validation_failed | 429:too_many_requests | 503:site_maintenance