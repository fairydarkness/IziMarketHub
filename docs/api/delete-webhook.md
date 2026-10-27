# delete-webhook

DELETE/api/public/v1/webhook
Право: webhooksИзменяющий
Удалить ссылку вебхука
Информация
Удаляет ссылку: вебхуки перестают уходить, недоставленное больше не отправляется. 204 без тела.
Право — webhooks.



## 204: Ссылка удалена

Ошибки: 401:public_api_key_invalid | 403:account_blocked,account_email_required,account_email_unverified,public_api_scope_missing | 404:webhook_endpoint_not_found | 429:too_many_requests | 503:site_maintenance