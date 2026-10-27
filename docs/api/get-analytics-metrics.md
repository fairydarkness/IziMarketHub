# get-analytics-metrics

GET/api/public/v1/analytics/metrics
Право: analytics:read
Показатели аналитики
Информация
Каталог показателей и блоков отчёта с подписями на языке Accept-Language и пределы периода — тот же, что в кабинете.
Право — analytics:read.



## 200: Каталог показателей
```json
{
  "data": {
    "metrics": [
      {
        "key": "earned",
        "label": "К получению",
        "group": "money",
        "group_label": "Деньги"
      },
      {
        "key": "commission",
        "label": "Комиссия площадки",
        "group": "money",
        "group_label": "Деньги"
      },
      {
        "key": "turnover",
        "label": "Оборот",
        "group": "money",
        "group_label": "Деньги"
      },
      {
        "key": "average_check",
        "label": "Средний чек",
        "group": "money",
        "group_label": "Деньги"
      },
      {
        "key": "cost",
        "label": "Себестоимость",
        "group": "money",
        "group_label": "Деньги"
      },
      {
        "key": "losses",
        "label": "Убытки возвратов",
        "group": "money",
        "group_label": "Деньги"
      },
      {
        "key": "profit",
        "label": "Прибыль",
        "group": "money",
        "group_label": "Деньги"
      },
      {
        "key": "margin",
        "label": "Маржа",
        "group": "money",
        "group_label": "Деньги"
      },
      {
        "key": "cost_coverage",
        "label": "Продажи с себестоимостью",
        "group": "money",
        "group_label": "Деньги"
      },
      {
        "key": "withdrawal_fees",
        "label": "Комиссия выводов",
        "group": "money",
        "group_label": "Деньги"
      },
      {
        "key": "net_profit",
        "label": "Прибыль за вычетом выводов",
        "group": "money",
        "group_label": "Деньги"
      },
      {
        "key": "sales",
        "label": "Продажи",
        "group": "deals",
        "group_label": "Сделки"
      },
      {
        "key": "orders",
        "label": "Заказы",
        "group": "deals",
        "group_label": "Сделки"
      },
      {
        "key": "cancelled",
        "label": "Отмены",
        "group": "deals",
        "group_label": "Сделки"
      },
      {
        "key": "refunded",
        "label": "Возвраты",
        "group": "deals",
        "group_label": "Сделки"
      },
      {
        "key": "disputes",
        "label": "Споры",
        "group": "quality",
        "group_label": "Качество"
      },
      {
        "key": "dispute_rate",
        "label": "Доля споров",
        "group": "quality",
        "group_label": "Качество"
      },
      {
        "key": "refund_rate",
        "label": "Доля возвратов",
        "group": "quality",
        "group_label": "Качество"
      },
      {
        "key": "rating",
        "label": "Рейтинг",
        "group": "quality",
        "group_label": "Качество"
      },
      {
        "key": "views",
        "label": "Просмотры",
        "group": "audience",
        "group_label": "Просмотры"
      },
      {
        "key": "conversion",
        "label": "Конверсия",
        "group": "audience",
        "group_label": "Просмотры"
      }
    ],
    "sections": [
      {
        "key": "days",
        "label": "График по суткам"
      },
      {
        "key": "top_products",
        "label": "Лучшие товары"
      }
    ],
    "period": {
      "default_days": 30,
      "max_days": 365
    }
  },
  "status": true
}
```

Ошибки: 401:public_api_key_invalid | 403:account_blocked,account_email_required,account_email_unverified,public_api_scope_missing | 429:too_many_requests | 503:site_maintenance