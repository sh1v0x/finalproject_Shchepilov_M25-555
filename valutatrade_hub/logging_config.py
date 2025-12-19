from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from valutatrade_hub.infra.settings import SettingsLoader


def setup_logging() -> None:
    """
    Настройка логов приложения.

    Формат: человекочитаемый строковый.
    Ротация: RotatingFileHandler (по размеру).
    Уровень: INFO (по умолчанию), можно переопределить через SettingsLoader.
    """
    settings = SettingsLoader()
    log_level = str(settings.get("LOG_LEVEL", "INFO")).upper()
    log_dir = Path(str(settings.get("LOG_DIR", "logs")))
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "actions.log"

    fmt = str(
        settings.get(
            "LOG_FORMAT",
            "%(levelname)s %(asctime)s %(name)s %(message)s",
        )
    )

    level = getattr(logging, log_level, logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)

    # Не плодим хэндлеры при повторных setup_logging()
    if any(isinstance(h, RotatingFileHandler) for h in root.handlers):
        return

    handler = RotatingFileHandler(
        log_file,
        maxBytes=1_000_000,  # ~1MB
        backupCount=3,
        encoding="utf-8",
    )
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(fmt))

    root.addHandler(handler)
