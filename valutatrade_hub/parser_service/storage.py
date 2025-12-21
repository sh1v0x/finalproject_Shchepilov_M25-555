from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def load_history(path: Path) -> list[dict[str, Any]]:
    """
    Загружает историю измерений из exchange_rates.json.
    Формат файла: JSON-массив объектов.
    """
    if not path.exists():
        return []

    data = json.loads(path.read_text(encoding="utf-8") or "[]")
    if not isinstance(data, list):
        raise ValueError("exchange_rates.json must contain a list")

    for item in data:
        if not isinstance(item, dict):
            raise ValueError("exchange_rates.json must contain a list of objects")
    return data


def append_history_record(path: Path, record: dict[str, Any]) -> None:
    """
    Добавляет запись в историю атомарно:
    временный файл -> rename.
    Не добавляет дубликаты по record['id'].
    """
    history = load_history(path)

    rec_id = record.get("id")
    if not isinstance(rec_id, str) or rec_id.strip() == "":
        raise ValueError("History record must contain non-empty string field 'id'")

    if any(isinstance(x, dict) and x.get("id") == rec_id for x in history):
        return 

    history.append(record)

    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(
        json.dumps(history, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp_path.replace(path)


def load_snapshot(path: Path) -> dict[str, Any]:
    """
    Загружает snapshot rates.json.
    Формат:
      {
        "pairs": { 
            "BTC_USD": {
                "rate": ..., 
                "updated_at": "...", 
                "source": "..."
            },
        },
        "last_refresh": "..."
      }
    """
    if not path.exists():
        return {"pairs": {}, "last_refresh": None}

    raw = path.read_text(encoding="utf-8") or "{}"
    data = json.loads(raw)

    if not isinstance(data, dict):
        raise ValueError("rates.json must contain an object")

    pairs = data.get("pairs")
    if pairs is None:
        pairs = {}
    if not isinstance(pairs, dict):
        raise ValueError("rates.json: 'pairs' must be an object")

    last_refresh = data.get("last_refresh")
    if last_refresh is not None and not isinstance(last_refresh, str):
        raise ValueError("rates.json: 'last_refresh' must be string or null")

    return {"pairs": pairs, "last_refresh": last_refresh}


def upsert_snapshot_pair(
    path: Path,
    pair: str,
    rate: float,
    updated_at: str,
    source: str,
) -> bool:
    """
    Обновляет одну пару в snapshot по правилу:
    - если пары нет -> записать
    - если есть, но updated_at свежее текущего -> заменить
    Возвращает True, если snapshot был изменён.
    """
    snap = load_snapshot(path)
    pairs = snap["pairs"]

    if not isinstance(rate, (int, float)) or float(rate) <= 0:
        raise ValueError("rate must be positive number")
    if not isinstance(updated_at, str) or updated_at.strip() == "":
        raise ValueError("updated_at must be non-empty string")
    if not isinstance(source, str) or source.strip() == "":
        raise ValueError("source must be non-empty string")

    old = pairs.get(pair)
    changed = False

    if not isinstance(old, dict):
        pairs[pair] = {"rate": float(rate), "updated_at": updated_at, "source": source}
        changed = True
    else:
        old_updated = old.get("updated_at")
        if not isinstance(old_updated, str) or updated_at > old_updated:
            pairs[pair] = {
                "rate": float(rate), 
                "updated_at": updated_at, 
                "source": source,
            }
            changed = True

    if changed:
        snap["pairs"] = pairs
        snap["last_refresh"] = updated_at

        tmp_path = path.with_suffix(path.suffix + ".tmp")
        tmp_path.write_text(
            json.dumps(snap, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp_path.replace(path)

    return changed


@dataclass(frozen=True)
class RatesStorage:
    snapshot_path: Path
    history_path: Path

    def write_cache(self, payload: dict[str, Any]) -> int:
        """
        Записывает snapshot в rates.json в формате Core Service:
        {
            "pairs": { 
                "BTC_USD": {
                    "rate": ..., 
                    "updated_at": "...", 
                    "source": "..."
                },
            },
          "last_refresh": "..."
        }

        Возвращает количество реально обновлённых пар.
        """
        pairs = payload.get("pairs", {})
        if not isinstance(pairs, dict):
            raise ValueError("payload['pairs'] must be a dict")

        updated_count = 0
        for pair, item in pairs.items():
            if not isinstance(item, dict):
                continue

            rate = item.get("rate")
            updated_at = item.get("updated_at")
            source = item.get("source")

            if not isinstance(pair, str) or pair.strip() == "":
                continue
            if not isinstance(rate, (int, float)) or float(rate) <= 0:
                continue
            if not isinstance(updated_at, str) or updated_at.strip() == "":
                continue
            if not isinstance(source, str) or source.strip() == "":
                continue

            changed = upsert_snapshot_pair(
                path=self.snapshot_path,
                pair=pair,
                rate=float(rate),
                updated_at=updated_at,
                source=source,
            )
            if changed:
                updated_count += 1

        return updated_count

    def append_history(self, record: dict[str, Any]) -> None:
        """
        Добавляет запись в exchange_rates.json (история измерений).
        """
        append_history_record(self.history_path, record)
