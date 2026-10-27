# create-product

POST/api/public/v1/products
Право: products:writeИзменяющийIdempotency-Key
Создать товар
Информация
Выставить товар либо сохранить черновик ("draft": true) — тем же кодом, что форма сайта: премодерация подкатегории (status: pending), разделы только для верифицированных, границы цены и количества из схемы, поля по схеме — и отказы те же. Ответ — товар целиком; его же отдаёт GET /products/{product}.
Деньги — рубли в копейках: price_minor и cost_minor; заголовок X-Currency не читается.
subcategory_id — из GET /catalog/tree, attrs — значения полей source: seller схемы по key.
images — id загрузок POST /media, до 10, в порядке показа; кроме черновика — хотя бы одна.
Кроме черновика нужно название на каждом языке сайта, кроме основного (translations).
parameters — параметры лота: группы вариантов с надбавкой к цене единицы и вопросы покупателю. Что выбрал покупатель, приходит в buyer.parameters сделки и вебхуков order.*.
Принимает Idempotency-Key: повтор после обрыва связи получает ответ первого запроса и ничего не создаёт.
Право — products:write.
Параметры
Заголовки
Idempotency-Keystring
Ключ повтора: 8–120 знаков — латиница, цифры, - и _; свой у продавца, живёт сутки. Тот же запрос с тем же ключом получает ответ первого и заголовок Idempotent-Replayed: true; другой запрос с тем же ключом — 409 public_api_idempotency_conflict; первый ещё выполняется — 409 public_api_idempotency_in_progress. Отказ ключ не занимает.
Шаблон:^[A-Za-z0-9_-]{8,120}$
Тело запроса · JSON
titleОбязательныйstring · от 3 до 160 знаков
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
price_minorОбязательныйinteger · 0–100 000 000 000
Цена в копейках рубля, которую называет продавец; у склада и валюты — цена единицы
pricing_modestring
Значения:deductmarkup
cost_minorinteger или null · ≥ 0
Себестоимость единицы; видна только продавцу
quantityОбязательныйinteger · 1–100 000
Сколько единиц, в границах схемы; у услуги — сколько заказов продавец готов взять
min_order_quantityinteger или null · 1–100 000
Свой минимум к покупке — только у currency и stock (иначе 422 min_order_quantity_not_supported), не выше settings.max_order_quantity схемы (иначе 422 validation_failed по min_order_quantity). Ниже минимума раздела ничего не меняет: действует больший. Нет или null — как в разделе
subcategory_idОбязательныйinteger · ≥ 1
—
attrsobject
Значения полей source: seller схемы по key; у варианта custom — ещё своё значение в <key>__custom
parametersмассив object или null · до 10 элементов
Параметры лота по порядку показа: группы radio и checkbox с вариантами и надбавкой к цене единицы, вопросы покупателю text и textarea. У нового лота — без id. Пределы: до 10 групп, до 50 вариантов, заголовок до 100 знаков, подпись до 150. Самый дешёвый и самый дорогой выбор держат цену единицы в границах подкатегории — иначе 422 validation_failed по parameters. Пароль текстовым параметром не спрашивают. Нет или null — без параметров
imagesмассив string · до 10 элементов
id загрузок POST /media в порядке показа; кроме черновика — хотя бы одна
draftboolean · по умолчанию false
true — черновик: модератору и в продажу не уходит



## 201: Товар создан
```json
$33
```

Ошибки: 401:public_api_key_invalid | 403:account_blocked,account_email_required,account_email_unverified,public_api_scope_missing,seller_not_verified | 409:drafts_limit_reached,public_api_idempotency_conflict,public_api_idempotency_in_progress | 422:image_not_available,min_order_quantity_not_supported,price_below_minimum_commission,price_out_of_range,public_api_idempotency_key_invalid,stop_phrase_found,subcategory_not_available,too_many_images,validation_failed | 429:too_many_requests | 503:site_maintenance