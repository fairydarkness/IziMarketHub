# list-orders

GET/api/public/v1/orders
Право: orders:read
Список сделок
Информация
Свои продажи — сделки, где владелец ключа продавец; покупок здесь нет. Без updated_since — от свежих к старым по созданию; с ним — от давно изменённых к недавним. Курсор next_cursor непрозрачный и годится только для того же запроса: испорченный или от другого порядка даёт первую страницу. Выданного, заметок, полей выдачи, почты и адреса сети покупателя в ответе нет.
Синхронизация «хотя бы один раз». Храните наибольший полученный updated_at, а следующий опрос начинайте с него минус минута; повторы отсеивайте по паре id и updated_at. Вебхуки order.* приходят сразу — опрос нужен, чтобы ничего не пропустить.
Право — orders:read.
Параметры
Строка запроса
statusstring
Только сделки в этом статусе
Значения:paiddelivereddisputedcompletedcancelledrefunded
created_fromstring · date-time
Создана не раньше — граница входит; дата без времени — её полночь UTC
created_tostring · date-time
Создана раньше — граница не входит
product_idstring · uuid
Только сделки по этому товару
updated_sincestring · date-time
Изменена не раньше — граница входит; задан — список по возрастанию изменения
cursorstring · до 255 знаков
next_cursor предыдущей страницы того же запроса
limitinteger · 1–50 · по умолчанию 20
Сделок на странице



## 200: Страница сделок
```json
{
  "data": {
    "items": [
      {
        "id": "01a13c13-f761-7231-92ec-6f80c06ee40b",
        "status": "completed",
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
        "deliver_due_at": "2026-10-14T12:00:00+00:00",
        "delivered_at": "2026-10-13T12:01:00+00:00",
        "confirm_due_at": "2026-10-16T12:00:00+00:00",
        "closed_at": "2026-10-13T14:00:00+00:00",
        "payout_due_at": "2026-10-16T12:00:00+00:00",
        "paid_out_at": null,
        "updated_at": "2026-10-14T12:00:00+00:00",
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
              "title_ru": "Номинал",
              "title_en": "Amount",
              "options": [
                {
                  "option_id": 32,
                  "label_ru": "5000 шт.",
                  "label_en": "5000 pcs",
                  "price_delta_minor": 316000
                }
              ],
              "value": null
            },
            {
              "group_id": 13,
              "type": "text",
              "title_ru": "Ник в игре",
              "title_en": "In-game nickname",
              "options": [],
              "value": "kiwi_in_game"
            }
          ]
        }
      }
    ],
    "has_next_page": false,
    "next_cursor": null
  },
  "status": true
}
```

Ошибки: 401:public_api_key_invalid | 403:account_blocked,account_email_required,account_email_unverified,public_api_scope_missing | 422:validation_failed | 429:too_many_requests | 503:site_maintenance