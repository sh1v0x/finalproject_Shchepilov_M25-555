from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None  # type: ignore[assignment]


class SettingsLoader:
    """
    Singleton для конфигурации приложения.

    Реализация через __new__:
    - простой и читаемый способ для одного класса;
    - гарантирует один экземпляр в процессе;
    - предотвращает создание новых экземпляров при повторных импортах.
    """

    _instance: "SettingsLoader | None" = None
    _loaded: bool = False
    _config: dict[str, Any]

    def __new__(cls) -> "SettingsLoader":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config = {}
        return cls._instance

    def _load_from_pyproject(self) -> dict[str, Any]:
        """
        Читает настройки из pyproject.toml (секция [tool.valutatrade]).
        Если файл/секция отсутствуют — вернёт пустой dict.
        """
        pyproject_path = Path.cwd() / "pyproject.toml"
        if not pyproject_path.exists() or tomllib is None:
            return {}

        try:
            data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return {}

        tool = data.get("tool", {})
        if not isinstance(tool, dict):
            return {}

        vt = tool.get("valutatrade", {})
        if not isinstance(vt, dict):
            return {}

        return vt

    def _build_defaults(self) -> dict[str, Any]:
        """
        Дефолты проекта (минимальные ключи по ТЗ):
        - пути к JSON
        - TTL курсов
        - базовая валюта
        - формат логов/путь к логам (пока только ключи)
        """
        root = Path.cwd()
        data_dir = root / "data"

        return {
            "DATA_DIR": str(data_dir),
            "USERS_JSON": str(data_dir / "users.json"),
            "PORTFOLIOS_JSON": str(data_dir / "portfolios.json"),
            "RATES_JSON": str(data_dir / "rates.json"),
            "RATES_TTL_SECONDS": 300,
            "BASE_CURRENCY": "USD",
            "LOG_LEVEL": "INFO",
            "LOG_DIR": str(root / "logs"),
            "LOG_FORMAT": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        }

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return

        cfg = self._build_defaults()
        from_pyproject = self._load_from_pyproject()

        # pyproject значения имеют приоритет
        for k, v in from_pyproject.items():
            cfg[k] = v

        self._config = cfg
        self._loaded = True

    def get(self, key: str, default: Any = ...) -> Any:
        self._ensure_loaded()
        if default is ...:
            return self._config[key]
        return self._config.get(key, default)

    def reload(self) -> None:
        """Принудительная перезагрузка конфигурации."""
        self._loaded = False
        self._ensure_loaded()
