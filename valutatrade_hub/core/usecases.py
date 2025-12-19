from __future__ import annotations

from pathlib import Path
from typing import Any

from valutatrade_hub.core.utils import (
    data_dir,
    generate_salt,
    hash_password,
    load_json,
    normalize_username,
    now_iso,
    save_json,
    validate_password,
)

USERS_FILE: Path = data_dir() / "users.json"
PORTFOLIOS_FILE: Path = data_dir() / "portfolios.json"


def _load_users() -> list[dict[str, Any]]:
    data = load_json(USERS_FILE, default=[])
    if not isinstance(data, list):
        raise ValueError("users.json must contain a list")
    return data


def _save_users(users: list[dict[str, Any]]) -> None:
    save_json(USERS_FILE, users)


def _load_portfolios() -> list[dict[str, Any]]:
    data = load_json(PORTFOLIOS_FILE, default=[])
    if not isinstance(data, list):
        raise ValueError("portfolios.json must contain a list")
    return data


def _save_portfolios(portfolios: list[dict[str, Any]]) -> None:
    save_json(PORTFOLIOS_FILE, portfolios)


def _next_user_id(users: list[dict[str, Any]]) -> int:
    if not users:
        return 1
    # user_id автоинкремент: max + 1
    max_id = max(int(u["user_id"]) for u in users if "user_id" in u)
    return max_id + 1


def register_user(username: str, password: str) -> tuple[int, str]:
    """
    Регистрирует пользователя и создаёт пустой портфель.
    Возвращает (user_id, username).
    """
    username_norm = normalize_username(username)
    validate_password(password)

    users = _load_users()

    if any(u.get("username") == username_norm for u in users):
        raise ValueError(f"Имя пользователя '{username_norm}' уже занято")

    user_id = _next_user_id(users)
    salt = generate_salt()
    hashed = hash_password(password, salt)

    users.append(
        {
            "user_id": user_id,
            "username": username_norm,
            "hashed_password": hashed,
            "salt": salt,
            "registration_date": now_iso(),
        }
    )
    _save_users(users)

    portfolios = _load_portfolios()
    portfolios.append(
        {
            "user_id": user_id,
            "wallets": {},
        }
    )
    _save_portfolios(portfolios)

    return user_id, username_norm
