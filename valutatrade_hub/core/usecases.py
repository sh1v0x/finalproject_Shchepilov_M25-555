from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
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
from valutatrade_hub.infra.settings import SettingsLoader

USERS_FILE: Path = data_dir() / "users.json"
PORTFOLIOS_FILE: Path = data_dir() / "portfolios.json"
RATES_FILE: Path = data_dir() / "rates.json"


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



def login_user(username: str, password: str) -> tuple[int, str]:
    """
    Проверяет логин/пароль.
    Возвращает (user_id, username).
    """
    username_norm = normalize_username(username)
    validate_password(password)

    users = _load_users()

    user = next((u for u in users if u.get("username") == username_norm), None)
    if user is None:
        raise ValueError(f"Пользователь '{username_norm}' не найден")

    salt = user.get("salt")
    stored_hash = user.get("hashed_password")
    if not isinstance(salt, str) or not isinstance(stored_hash, str):
        raise ValueError("Некорректные данные пользователя в users.json")

    candidate_hash = hash_password(password, salt)
    if candidate_hash != stored_hash:
        raise ValueError("Неверный пароль")

    return int(user["user_id"]), username_norm



def _normalize_currency_code(code: str) -> str:
    if not isinstance(code, str):
        raise TypeError("currency_code must be str")
    value = code.strip().upper()
    if value == "":
        raise ValueError("currency_code cannot be empty")
    return value



def _load_rates() -> dict[str, Any]:
    data = load_json(RATES_FILE, default={})
    if not isinstance(data, dict):
        raise ValueError("rates.json must contain an object")
    return data



def _get_rate(from_code: str, to_code: str) -> float:
    """
    Единый контракт получения курса.
    Сначала пробуем rates.json, если там нет — используем заглушку.
    """
    f = _normalize_currency_code(from_code)
    t = _normalize_currency_code(to_code)
    if f == t:
        return 1.0

    pair = f"{f}_{t}"
    rates = _load_rates()
    if pair in rates and isinstance(rates[pair], dict) and "rate" in rates[pair]:
        rate_val = rates[pair]["rate"]
        if isinstance(rate_val, (int, float)) and rate_val > 0:
            return float(rate_val)

    # Заглушка (пока Parser Service не подключён)
    # 1 единица валюты = сколько в USD
    to_usd: dict[str, float] = {
        "USD": 1.0,
        "EUR": 1.07,
        "BTC": 59337.21,
        "RUB": 0.01016,
        "ETH": 3720.0,
    }

    if t == "USD":
        if f not in to_usd:
            raise CurrencyNotFoundError(f)
        return to_usd[f]

    if t not in to_usd:
        raise CurrencyNotFoundError(t)
    if f not in to_usd:
        raise CurrencyNotFoundError(f)

    return to_usd[f] / to_usd[t]



def _load_user_portfolio(user_id: int) -> dict[str, float]:
    portfolios = _load_portfolios()
    record = next((p for p in portfolios if int(p.get("user_id", -1)) == user_id), None)
    if record is None:
        return {}

    wallets = record.get("wallets", {})
    if not isinstance(wallets, dict):
        raise ValueError("portfolios.json: wallets must be an object")

    result: dict[str, float] = {}
    for code, payload in wallets.items():
        c = _normalize_currency_code(code)
        if isinstance(payload, dict) and "balance" in payload:
            bal = payload["balance"]
        else:
            bal = None

        if not isinstance(bal, (int, float)):
            raise ValueError(f"Invalid balance for {c}")

        result[c] = float(bal)

    return result



def build_portfolio_report(user_id: int, base_currency: str = "USD") -> dict[str, Any]:
    """
    Возвращает данные для вывода show-portfolio:
    - base
    - items: [{currency_code, balance, value_in_base}]
    - total
    """
    base = _normalize_currency_code(base_currency)
    
    # Валидация base даже при пустом портфеле
    _get_rate("USD", base)


    wallets = _load_user_portfolio(user_id)
    items: list[dict[str, Any]] = []
    total = 0.0

    for code, balance in wallets.items():
        rate = _get_rate(code, base)
        value_in_base = balance * rate
        items.append(
            {
                "currency_code": code,
                "balance": balance,
                "value_in_base": value_in_base,
            }
        )
        total += value_in_base

    # стабильно сортируем для красивого вывода
    items.sort(key=lambda x: x["currency_code"])

    return {
        "base": base,
        "items": items,
        "total": total,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }



def _save_user_wallet_balance(
        user_id: int, 
        currency_code: str, 
        new_balance: float
    ) -> None:
    portfolios = _load_portfolios()
    record = next((p for p in portfolios if int(p.get("user_id", -1)) == user_id), None)

    if record is None:
        # На всякий случай (в норме портфель создаётся при register)
        record = {"user_id": user_id, "wallets": {}}
        portfolios.append(record)

    wallets = record.get("wallets")
    if not isinstance(wallets, dict):
        raise ValueError("portfolios.json: wallets must be an object")

    code = _normalize_currency_code(currency_code)
    wallets[code] = {"balance": float(new_balance)}
    record["wallets"] = wallets

    _save_portfolios(portfolios)



def _validate_amount_positive(amount: float) -> float:
    if not isinstance(amount, (int, float)):
        raise TypeError("'amount' должен быть положительным числом")
    value = float(amount)
    if value <= 0:
        raise ValueError("'amount' должен быть положительным числом")
    return value



def buy_currency(
    user_id: int,
    currency_code: str,
    amount: float,
    base_currency: str = "USD",
) -> dict[str, Any]:
    """
    Покупка валюты:
      - валидируем currency и amount
      - если кошелька нет — создаём
      - увеличиваем баланс на amount
      - опционально считаем оценочную стоимость по курсу currency->base
    Возвращает данные для печати в CLI.
    """
    code = _normalize_currency_code(currency_code)
    base = _normalize_currency_code(base_currency)
    amt = _validate_amount_positive(amount)

    wallets = _load_user_portfolio(user_id)

    before = wallets.get(code, 0.0)
    after = before + amt

    # Обновляем портфель 
    _save_user_wallet_balance(user_id, code, after)

    # Курс и стоимость 
    try:
        rate = _get_rate(code, base)  # base per 1 currency
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Не удалось получить курс для {code}→{base}") from exc

    cost = amt * rate

    return {
        "currency": code,
        "amount": amt,
        "base": base,
        "rate": rate,
        "before": before,
        "after": after,
        "cost": cost,
    }



def sell_currency(
    user_id: int,
    currency_code: str,
    amount: float,
    base_currency: str = "USD",
) -> dict[str, Any]:
    """
    Продажа валюты:
      - валидируем currency и amount
      - проверяем наличие кошелька и достаточность средств
      - уменьшаем баланс
      - опционально: начисляем выручку в base (USD) кошелёк
    """
    code = _normalize_currency_code(currency_code)
    base = _normalize_currency_code(base_currency)
    amt = _validate_amount_positive(amount)

    wallets = _load_user_portfolio(user_id)

    if code not in wallets:
        raise ValueError(
            f"У вас нет кошелька '{code}'. Добавьте валюту: "
            "она создаётся автоматически при первой покупке."
        )

    before = wallets[code]
    if amt > before:
        raise InsufficientFundsError(available=before, required=amt, code=code)

    after = before - amt
    _save_user_wallet_balance(user_id, code, after)

    # Оценочная выручка в base по курсу code->base
    try:
        rate = _get_rate(code, base)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Не удалось получить курс для {code}→{base}") from exc

    revenue = amt * rate

    # Опционально: начисляем выручку в base-кошелёк (например, USD)
    if code != base:
        base_before = wallets.get(base, 0.0)
        base_after = base_before + revenue
        _save_user_wallet_balance(user_id, base, base_after)

    return {
        "currency": code,
        "amount": amt,
        "base": base,
        "rate": rate,
        "before": before,
        "after": after,
        "revenue": revenue,
    }


def _parse_iso_dt(value: str) -> datetime | None:
    if not isinstance(value, str) or value.strip() == "":
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _is_fresh(updated_at_iso: str, max_age_seconds: int = 300) -> bool:
    dt = _parse_iso_dt(updated_at_iso)
    if dt is None:
        return False
    age = (datetime.now() - dt).total_seconds()
    return age <= max_age_seconds


def get_rate_with_cache(
    from_code: str,
    to_code: str,
    max_age_seconds: int | None = None,
) -> dict[str, Any]:
    """
    Возвращает курс from->to с учётом кеша rates.json.
    Если кеш свежий (<= max_age_seconds) — берём его.
    Иначе — получаем через заглушку (_get_rate) и обновляем кеш.

    Возвращает:
      {
        "from": "USD",
        "to": "BTC",
        "rate": 0.00001685,
        "updated_at": "2025-10-09T00:03:22",
        "reverse_rate": 59337.21
      }
    """
    f = _normalize_currency_code(from_code)
    t = _normalize_currency_code(to_code)

    if max_age_seconds is None:
        max_age_seconds = int(SettingsLoader().get("RATES_TTL_SECONDS", 300))

    pair = f"{f}_{t}"

    rates = _load_rates()
    cached = rates.get(pair)

    if isinstance(cached, dict) and "rate" in cached and "updated_at" in cached:
        rate_val = cached.get("rate")
        upd = cached.get("updated_at")
        if isinstance(rate_val, (int, float)) and isinstance(upd, str):
            if float(rate_val) > 0 and _is_fresh(upd, max_age_seconds=max_age_seconds):
                reverse = 1.0 / float(rate_val)
                return {
                    "from": f,
                    "to": t,
                    "rate": float(rate_val),
                    "updated_at": upd,
                    "reverse_rate": reverse,
                }

    # Кеш отсутствует или устарел, берём из заглушки и обновляем кеш
    try:
        rate = _get_rate(f, t)
    except CurrencyNotFoundError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise ApiRequestError(f"не удалось получить курс {f}→{t}") from exc

    updated_at = datetime.now().isoformat(timespec="seconds")
    rates[pair] = {"rate": rate, "updated_at": updated_at}

    # Сервис-метаданные
    rates["source"] = "Stub"
    rates["last_refresh"] = updated_at

    save_json(RATES_FILE, rates)

    reverse_rate = 1.0 / rate if rate != 0 else 0.0
    return {
        "from": f,
        "to": t,
        "rate": rate,
        "updated_at": updated_at,
        "reverse_rate": reverse_rate,
    }