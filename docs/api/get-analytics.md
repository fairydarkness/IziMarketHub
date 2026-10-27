# get-analytics

GET/api/public/v1/analytics
Право: analytics:read
Аналитика
Информация
Аналитика продавца за период — тот же отчёт, что в кабинете: показатели metrics за период from … to и за такой же отрезок перед ним (previous), блоки sections (days — по дню, top_products — лучшие товары). Каталог показателей и блоков — GET /analytics/metrics. Отличие от кабинета одно — деньги: {amount_minor, currency}, как во всём публичном API.
Право — analytics:read.
Параметры
Строка запроса
fromstring · date
Первые сутки периода; без поля — за 30 суток до to
tostring · date
Последние сутки включительно; без поля — сегодня
metricsstring · до 1 000 знаков
Показатели через запятую; без поля — все
sectionsstring · до 200 знаков
Блоки через запятую: days, top_products; без поля — все, пусто — ни одного



## 200: Отчёт за период
```json
{
  "data": {
    "period": {
      "from": "2026-10-08",
      "to": "2026-10-14",
      "days": 7,
      "previous_from": "2026-10-01",
      "previous_to": "2026-10-07",
      "timezone": "Europe/Moscow"
    },
    "metrics": [
      "earned",
      "sales"
    ],
    "sections": [
      "days"
    ],
    "current": {
      "earned": {
        "amount_minor": 71100,
        "currency": "RUB"
      },
      "sales": 1
    },
    "previous": {
      "earned": {
        "amount_minor": 0,
        "currency": "RUB"
      },
      "sales": 0
    },
    "days": [
      {
        "date": "2026-10-08",
        "earned": {
          "amount_minor": 0,
          "currency": "RUB"
        },
        "sales": 0
      },
      {
        "date": "2026-10-09",
        "earned": {
          "amount_minor": 0,
          "currency": "RUB"
        },
        "sales": 0
      },
      {
        "date": "2026-10-10",
        "earned": {
          "amount_minor": 0,
          "currency": "RUB"
        },
        "sales": 0
      },
      {
        "date": "2026-10-11",
        "earned": {
          "amount_minor": 0,
          "currency": "RUB"
        },
        "sales": 0
      },
      {
        "date": "2026-10-12",
        "earned": {
          "amount_minor": 0,
          "currency": "RUB"
        },
        "sales": 0
      },
      {
        "date": "2026-10-13",
        "earned": {
          "amount_minor": 71100,
          "currency": "RUB"
        },
        "sales": 1
      },
      {
        "date": "2026-10-14",
        "earned": {
          "amount_minor": 0,
          "currency": "RUB"
        },
        "sales": 0
      }
    ]
  },
  "status": true
}
```

Ошибки: 401:public_api_key_invalid | 403:account_blocked,account_email_required,account_email_unverified,public_api_scope_missing | 422:validation_failed | 429:too_many_requests | 503:site_maintenance