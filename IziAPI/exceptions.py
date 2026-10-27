"""Исключения клиента публичного API IziMarket."""

from __future__ import annotations


class IziAPIError(Exception):
    """Базовая ошибка API. ``code`` — машинный код из ``data.code``."""

    def __init__(self, status: int, code: str | None, message: str | None, data: dict | None = None,
                 retry_after: float | None = None):
        self.status = status
        self.code = code
        self.message = message
        self.data = data or {}
        self.retry_after = retry_after
        super().__init__(f"[{status}] {code}: {message}")


class InvalidKeyError(IziAPIError):
    """401 public_api_key_invalid — ключ неизвестен, истёк или отозван. Повтором не лечится."""


class ScopeMissingError(IziAPIError):
    """403 public_api_scope_missing — у ключа нет нужного права (в ``data['scope']``)."""


class AccountError(IziAPIError):
    """403 account_blocked / account_email_required / account_email_unverified."""


class NotFoundError(IziAPIError):
    """404 — сделки, товара или другого объекта нет."""


class ConflictError(IziAPIError):
    """409 — неверное состояние объекта, устаревшая version, конфликт ключа повтора."""


class ValidationError(IziAPIError):
    """422 — неверные параметры."""


class RateLimitError(IziAPIError):
    """429 too_many_requests — превышен лимит, ``retry_after`` в секундах."""


class MaintenanceError(IziAPIError):
    """503 site_maintenance — техработы."""


class NetworkError(Exception):
    """Запрос не дошёл или ответ не получен: неизвестно, выполнил ли его сервер."""


_BY_STATUS = {
    401: InvalidKeyError,
    404: NotFoundError,
    409: ConflictError,
    422: ValidationError,
    429: RateLimitError,
    503: MaintenanceError,
}


def make_error(status: int, code: str | None, message: str | None, data: dict | None,
               retry_after: float | None) -> IziAPIError:
    if status == 403:
        cls = ScopeMissingError if code == "public_api_scope_missing" else AccountError
    else:
        cls = _BY_STATUS.get(status, IziAPIError)
    return cls(status, code, message, data, retry_after)
