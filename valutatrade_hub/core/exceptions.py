from __future__ import annotations


class CurrencyError(Exception):
    """Базовая ошибка, связанная с валютами."""


class CurrencyNotFoundError(CurrencyError):
    """Выбрасывается, если валюта с указанным кодом отсутствует в реестре."""
