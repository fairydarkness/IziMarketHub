# list-webhook-deliveries

GET/api/public/v1/webhook/deliveries
Право: webhooks
Журнал доставок
Информация
Доставки продавца, свежие первыми, по 50 на страницу. status: pending — ждёт первой попытки, sent — попытка идёт, delivered, failed — ждёт повтора, dead — попытки кончились (восемь примерно за трое суток). Журнал хранит события и доставки 90 дней, тела ответов приёмника — 30.
Право — webhooks.
Параметры
Строка запроса
statusstring
Только доставки в этом статусе
Значения:pendingsentdeliveredfaileddead
typestring
Только события этого типа
Значения:product.status_changedproduct.moderation.approvedproduct.moderation.rejectedproduct.removedproduct.restoredproduct.needs_updateproduct.relocatedproduct.price_changedproduct.stock.depletedproduct.stock.lowproduct.stock.replenishedorder.createdorder.deliveredorder.redeliveredorder.disputedorder.completedorder.refundedorder.payout_releasedorder.delivery_requested
pageinteger · 1–50 000 · по умолчанию 1
Страница


Ошибки: 