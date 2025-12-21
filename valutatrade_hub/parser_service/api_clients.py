from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import requests

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.config import ParserConfig


class BaseApiClient(ABC):
    """Единый интерфейс для получения курсов из внешних API."""

    @abstractmethod
    def fetch_rates(self) -> dict[str, float]:
        """
        Возвращает курсы в стандартизированном формате:
        {"BTC_USD": 59337.21, "EUR_USD": 1.0786, ...}
        """
        raise NotImplementedError


class CoinGeckoClient(BaseApiClient):
    """
    Клиент CoinGecko для криптовалют.
    Возвращает пары вида <TICKER>_<BASE>, например BTC_USD.
    """

    def __init__(self, config: ParserConfig | None = None) -> None:
        self._config = config or ParserConfig()

    def fetch_rates(self) -> dict[str, float]:
        base = self._config.BASE_FIAT_CURRENCY.upper()
        vs = base.lower()

        ids = ",".join(self._config.CRYPTO_ID_MAP.values())
        params = {"ids": ids, "vs_currencies": vs}

        try:
            resp = requests.get(
                self._config.COINGECKO_URL,
                params=params,
                timeout=self._config.REQUEST_TIMEOUT,
            )
        except requests.exceptions.RequestException as exc:
            raise ApiRequestError(f"network error: {exc}") from exc

        if resp.status_code != 200:
            raise ApiRequestError(
                f"CoinGecko HTTP {resp.status_code}: {resp.text[:200]}"
            )

        try:
            payload: dict[str, Any] = resp.json()
        except ValueError as exc:
            raise ApiRequestError("CoinGecko: invalid JSON response") from exc

        result: dict[str, float] = {}
        # payload: {"bitcoin": {"usd": 59337.21}, ...}
        for ticker, cg_id in self._config.CRYPTO_ID_MAP.items():
            node = payload.get(cg_id)
            if not isinstance(node, dict):
                continue
            price = node.get(vs)
            if isinstance(price, (int, float)) and float(price) > 0:
                pair = f"{ticker}_{base}"
                result[pair] = float(price)

        return result


class ExchangeRateApiClient(BaseApiClient):
    """
    Клиент ExchangeRate-API для фиатных валют.
    ВАЖНО: API отдаёт rates как "1 USD = X EUR".
    Мы приводим к формату "1 EUR = Y USD" (то есть инвертируем).
    """

    def __init__(self, config: ParserConfig | None = None) -> None:
        self._config = config or ParserConfig()

    def fetch_rates(self) -> dict[str, float]:
        key = self._config.EXCHANGERATE_API_KEY
        if not key:
            raise ApiRequestError(
                "ExchangeRate-API key is missing. "
                "Set EXCHANGERATE_API_KEY environment variable."
            )

        base = self._config.BASE_FIAT_CURRENCY.upper()
        url = (
            f"{self._config.EXCHANGERATE_API_URL}/"
            f"{key}/latest/"
            f"{base}"
        )

        try:
            resp = requests.get(url, timeout=self._config.REQUEST_TIMEOUT)
        except requests.exceptions.RequestException as exc:
            raise ApiRequestError(f"network error: {exc}") from exc

        if resp.status_code != 200:
            raise ApiRequestError(
                f"ExchangeRate-API HTTP {resp.status_code}: {resp.text[:200]}"
            )

        try:
            payload: dict[str, Any] = resp.json()
        except ValueError as exc:
            raise ApiRequestError("ExchangeRate-API: invalid JSON response") from exc

        if payload.get("result") != "success":
            err = payload.get("error-type") or payload.get("result") or "unknown error"
            raise ApiRequestError(f"ExchangeRate-API error: {err}")

        rates = payload.get("conversion_rates")
        if not isinstance(rates, dict):
            rates = payload.get("rates")

        if not isinstance(rates, dict):
            raise ApiRequestError(
                "ExchangeRate-API: 'conversion_rates'/'rates' field missing or invalid"
            )
        
        result: dict[str, float] = {}
        # rates: {"EUR": 0.927, "RUB": 98.45, ...} meaning 1 USD = X CUR
        for cur in self._config.FIAT_CURRENCIES:
            cur_code = cur.upper()
            raw = rates.get(cur_code)
            if not isinstance(raw, (int, float)):
                continue
            raw_val = float(raw)
            if raw_val <= 0:
                continue

            # invert: 1 CUR = 1/raw USD  => CUR_USD
            pair = f"{cur_code}_{base}"
            result[pair] = 1.0 / raw_val

        return result