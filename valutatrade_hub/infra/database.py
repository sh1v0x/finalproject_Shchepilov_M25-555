from __future__ import annotations

from pathlib import Path
from typing import Any

from valutatrade_hub.core.utils import data_dir, load_json, save_json
from valutatrade_hub.infra.settings import SettingsLoader


class DatabaseManager:
    """
    Singleton-абстракция над JSON-хранилищем.

    Почему __new__:
    - проще всего для учебного проекта,
    - легко читается,
    - гарантирует один экземпляр при повторных импортах.
    """

    _instance: "DatabaseManager | None" = None

    def __new__(cls) -> "DatabaseManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _get_path(self, key: str, default_filename: str) -> Path:
        """
        Конфиг можно держать в SettingsLoader:
        USERS_FILE / PORTFOLIOS_FILE / RATES_FILE.
        Если ключ не задан — используем data_dir()/default_filename.
        """
        value = SettingsLoader().get(key, None)
        if isinstance(value, str) and value.strip():
            return Path(value)
        return data_dir() / default_filename

    def read_users(self) -> list[dict[str, Any]]:
        path = self._get_path("USERS_FILE", "users.json")
        data = load_json(path, default=[])
        if not isinstance(data, list):
            raise ValueError("users.json must contain a list")
        return data

    def write_users(self, users: list[dict[str, Any]]) -> None:
        path = self._get_path("USERS_FILE", "users.json")
        save_json(path, users)

    def read_portfolios(self) -> list[dict[str, Any]]:
        path = self._get_path("PORTFOLIOS_FILE", "portfolios.json")
        data = load_json(path, default=[])
        if not isinstance(data, list):
            raise ValueError("portfolios.json must contain a list")
        return data

    def write_portfolios(self, portfolios: list[dict[str, Any]]) -> None:
        path = self._get_path("PORTFOLIOS_FILE", "portfolios.json")
        save_json(path, portfolios)

    def read_rates(self) -> dict[str, Any]:
        path = self._get_path("RATES_FILE", "rates.json")
        data = load_json(path, default={})
        if not isinstance(data, dict):
            raise ValueError("rates.json must contain an object")
        return data

    def write_rates(self, rates: dict[str, Any]) -> None:
        path = self._get_path("RATES_FILE", "rates.json")
        save_json(path, rates)
