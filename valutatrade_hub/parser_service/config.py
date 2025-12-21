from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar


@dataclass(frozen=True)
class ParserConfig:
    """
    Конфигурация Parser Service.

    Все изменяемые параметры вынесены сюда:
    - API-ключи
    - эндпоинты
    - списки валют
    - пути к файлам
    """

    # ========= API KEYS =========
    # Ключ берётся из переменной окружения
    EXCHANGERATE_API_KEY: str | None = os.getenv("EXCHANGERATE_API_KEY")

    # ========= ENDPOINTS =========
    COINGECKO_URL: str = "https://api.coingecko.com/api/v3/simple/price"
    EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"

    # ========= CURRENCIES =========
    BASE_FIAT_CURRENCY: str = "USD"

    FIAT_CURRENCIES: tuple[str, ...] = (
        "EUR",
        "GBP",
        "RUB",
    )

    CRYPTO_CURRENCIES: tuple[str, ...] = (
        "BTC",
        "ETH",
        "SOL",
    )

    CRYPTO_ID_MAP: ClassVar[dict[str, str]] = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "SOL": "solana",
    }

    # ========= FILE PATHS =========
    DATA_DIR: Path = Path("data")

    RATES_FILE_PATH: Path = DATA_DIR / "rates.json"
    HISTORY_FILE_PATH: Path = DATA_DIR / "exchange_rates.json"

    # ========= NETWORK =========
    REQUEST_TIMEOUT: int = 10
