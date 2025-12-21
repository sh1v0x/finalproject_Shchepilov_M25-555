from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.logging_config import get_logger
from valutatrade_hub.parser_service.api_clients import BaseApiClient
from valutatrade_hub.parser_service.storage import RatesStorage


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class UpdateResult:
    updated: int
    last_refresh: str
    sources: dict[str, dict[str, Any]]
    had_errors: bool


class RatesUpdater:
    """
    Координатор обновления курсов:
    - опрашивает клиентов
    - объединяет курсы
    - сохраняет через storage в data/rates.json и историю (если storage поддерживает)
    """

    def __init__(
        self,
        clients: dict[str, BaseApiClient],
        storage: RatesStorage,
    ) -> None:
        self._clients = clients
        self._storage = storage
        self._log = get_logger("parser")

    def run_update(self) -> UpdateResult:
        self._log.info("Starting rates update...")

        combined: dict[str, dict[str, Any]] = {}
        sources_meta: dict[str, dict[str, Any]] = {}
        had_errors = False
        refresh_ts = _utc_iso()

        for source_name, client in self._clients.items():
            self._log.info("Fetching from %s...", source_name)

            try:
                rates = client.fetch_rates()
            except ApiRequestError as exc:
                had_errors = True
                self._log.error(
                    "Failed to fetch from %s: %s",
                    source_name,
                    str(exc),
                )
                sources_meta[source_name] = {
                    "ok": False,
                    "error": str(exc),
                    "count": 0,
                }
                continue

            count = 0
            for pair, rate in rates.items():
                # pair уже должен быть вида "BTC_USD" и rate > 0
                combined[pair] = {
                    "rate": float(rate),
                    "updated_at": refresh_ts,
                    "source": source_name,
                }
                count += 1

            self._log.info("Fetched from %s... OK (%s rates)", source_name, count)
            sources_meta[source_name] = {"ok": True, "count": count}

        if not combined:
            # ничего не удалось получить
            self._log.error("No rates fetched from any source.")
            raise ApiRequestError("не удалось получить курсы ни от одного источника")

        payload = {
            "pairs": combined,
            "last_refresh": refresh_ts,
            "sources": sources_meta,
        }

        self._log.info("Writing %s rates to cache...", len(combined))
        self._storage.write_cache(payload)
        self._log.info("Update finished. last_refresh=%s", refresh_ts)

        return UpdateResult(
            updated=len(combined),
            last_refresh=refresh_ts,
            sources=sources_meta,
            had_errors=had_errors,
        )


storage = RatesStorage(
    snapshot_path=Path("data/rates.json"),
    history_path=Path("data/exchange_rates.json"),
)