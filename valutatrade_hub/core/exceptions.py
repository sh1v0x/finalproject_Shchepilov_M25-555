from __future__ import annotations


class ValutaTradeError(Exception):
    """Базовая ошибка приложения."""


class CurrencyError(ValutaTradeError):
    """Ошибки, связанные с валютами."""


class CurrencyNotFoundError(CurrencyError):
    """Неизвестная валюта."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"Неизвестная валюта '{code}'")


class InsufficientFundsError(ValutaTradeError):
    """Недостаточно средств."""

    def __init__(self, available: float, required: float, code: str) -> None:
        self.available = available
        self.required = required
        self.code = code
        super().__init__(
            f"Недостаточно средств: доступно {available:.4f} {code}, "
            f"требуется {required:.4f} {code}"
        )


class ApiRequestError(ValutaTradeError):
    """Сбой внешнего API / источника курсов."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Ошибка при обращении к внешнему API: {reason}")
