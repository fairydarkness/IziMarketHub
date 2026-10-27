# get-balance

GET/api/public/v1/balance
Право: balance:read
Баланс
Информация
Баланс кошелька владельца ключа в форме вебхуков — {amount_minor, currency}, копейки: всего (balance), забронировано операциями (held), можно потратить сейчас (available = balance − held) и часть available, которую можно только тратить на покупки (spend_only: пополнения и оплаты снаружи).
Выплат здесь нет и не будет: ни суммы к выводу, ни долей продаж в холде, ни заявок на вывод.
Право — balance:read.



## 200: Баланс кошелька
```json
{
  "data": {
    "balance": {
      "amount_minor": 170000,
      "currency": "RUB"
    },
    "held": {
      "amount_minor": 0,
      "currency": "RUB"
    },
    "available": {
      "amount_minor": 170000,
      "currency": "RUB"
    },
    "spend_only": {
      "amount_minor": 20000,
      "currency": "RUB"
    },
    "currency": "RUB"
  },
  "status": true
}
```

Ошибки: 401:public_api_key_invalid | 403:account_blocked,account_email_required,account_email_unverified,public_api_scope_missing | 429:too_many_requests | 503:site_maintenance