from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from valutatrade_hub.core.exceptions import CurrencyNotFoundError


def _validate_code(code: str) -> str:
    if not isinstance(code, str):
        raise TypeError("code must be a string")

    value = code.strip().upper()
    if value == "":
        raise ValueError("code cannot be empty")

    # 2–5 символов, без пробелов (по ТЗ)
    if " " in value or not (2 <= len(value) <= 5):
        raise ValueError("code must be 2–5 uppercase characters without spaces")

    return value


def _validate_name(name: str) -> str:
    if not isinstance(name, str):
        raise TypeError("name must be a string")

    value = name.strip()
    if value == "":
        raise ValueError("name cannot be empty")

    return value


@dataclass(frozen=True, slots=True)
class Currency(ABC):
    """
    Абстрактная валюта (унифицированный интерфейс).
    Public-атрибуты:
      - name: человекочитаемое имя
      - code: тикер/ISO-код (2–5 символов, UPPER)
    """

    name: str
    code: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _validate_name(self.name))
        object.__setattr__(self, "code", _validate_code(self.code))

    @abstractmethod
    def get_display_info(self) -> str:
        """Строковое представление для UI/логов."""
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class FiatCurrency(Currency):
    issuing_country: str

    def __post_init__(self) -> None:
        super().__post_init__()
        object.__setattr__(
            self,
            "issuing_country",
            _validate_name(self.issuing_country),
        )
    def get_display_info(self) -> str:
        # Формат из ТЗ:
        # "[FIAT] USD — US Dollar (Issuing: United States)"
        return f"[FIAT] {self.code} — {self.name} (Issuing: {self.issuing_country})"


@dataclass(frozen=True, slots=True)
class CryptoCurrency(Currency):
    algorithm: str
    market_cap: float

    def __post_init__(self) -> None:
        super().__post_init__()
        object.__setattr__(self, "algorithm", _validate_name(self.algorithm))
        if not isinstance(self.market_cap, (int, float)):
            raise TypeError("market_cap must be a number")
        if float(self.market_cap) < 0:
            raise ValueError("market_cap cannot be negative")
        object.__setattr__(self, "market_cap", float(self.market_cap))

    def get_display_info(self) -> str:
        # Формат из ТЗ:
        # "[CRYPTO] BTC — Bitcoin (Algo: SHA-256, MCAP: 1.12e12)"
        return (
            f"[CRYPTO] {self.code} — {self.name} "
            f"(Algo: {self.algorithm}, MCAP: {self.market_cap:.2e})"
        )


# -------------------------
# Реестр валют (минимальный)
# -------------------------
_CURRENCY_REGISTRY: dict[str, Currency] = {
    "USD": FiatCurrency(name="US Dollar", code="USD", issuing_country="United States"),
    "EUR": FiatCurrency(name="Euro", code="EUR", issuing_country="Eurozone"),
    "BTC": CryptoCurrency(
        name="Bitcoin",
        code="BTC",
        algorithm="SHA-256",
        market_cap=1.12e12,
    ),
    "ETH": CryptoCurrency(
        name="Ethereum",
        code="ETH",
        algorithm="Ethash",
        market_cap=4.50e11,
    ),
}


def get_currency(code: str) -> Currency:
    """
    Фабрика получения валюты по коду.
    Если код неизвестен — бросает CurrencyNotFoundError.
    """
    norm = _validate_code(code)
    currency = _CURRENCY_REGISTRY.get(norm)
    if currency is None:
        raise CurrencyNotFoundError(f"Currency code '{norm}' not found")
    return currency
