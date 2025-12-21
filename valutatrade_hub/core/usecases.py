from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from valutatrade_hub.core.currencies import get_currency
from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.core.models import Wallet
from valutatrade_hub.core.utils import (
    generate_salt,
    hash_password,
    normalize_username,
    now_iso,
    validate_password,
)
from valutatrade_hub.decorators import log_action
from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.infra.settings import SettingsLoader


def validate_currency_code(code: str) -> str:
    """
    Валидирует валютный код через реестр currencies.get_currency().
    Возвращает нормализованный code (upper).
    """
    cur = get_currency(code)  
    return cur.code


def _load_users() -> list[dict[str, Any]]:
    return DatabaseManager().read_users()


def _save_users(users: list[dict[str, Any]]) -> None:
    DatabaseManager().write_users(users)


def _load_portfolios() -> list[dict[str, Any]]:
    return DatabaseManager().read_portfolios()


def _save_portfolios(portfolios: list[dict[str, Any]]) -> None:
    DatabaseManager().write_portfolios(portfolios)

def _load_rates() -> dict[str, Any]:
    return DatabaseManager().read_rates()

def _update_user_wallet(
    user_id: int,
    currency_code: str,
    updater: Callable[[float], float],
) -> tuple[float, float]:
    """
    Безопасная операция: чтение → модификация → запись.
    updater принимает текущий balance и возвращает новый balance.
    Возвращает (before, after).
    """
    portfolios = _load_portfolios()
    record = next((p for p in portfolios if int(p.get("user_id", -1)) == user_id), None)
    if record is None:
        # если портфеля нет — создадим запись
        record = {"user_id": user_id, "wallets": {}}
        portfolios.append(record)

    wallets = record.get("wallets")
    if not isinstance(wallets, dict):
        raise ValueError("portfolios.json: wallets must be an object")

    code = validate_currency_code(currency_code)

    payload = wallets.get(code, {})
    if isinstance(payload, dict) and isinstance(payload.get("balance"), (int, float)):
        before = float(payload["balance"])
    elif code in wallets:
        raise ValueError(f"Invalid wallet payload for {code}")
    else:
        before = 0.0

    after = float(updater(before))

    wallets[code] = {"balance": after}
    record["wallets"] = wallets

    _save_portfolios(portfolios)
    return before, after



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
    
    get_rate_with_cache("USD", base)

    wallets = _load_user_portfolio(user_id)
    items: list[dict[str, Any]] = []
    total = 0.0

    for code, balance in wallets.items():
        rate = get_rate_with_cache(code, base)["rate"]
        value_in_base = balance * rate
        items.append(
            {
                "currency_code": code,
                "balance": balance,
                "value_in_base": value_in_base,
            }
        )
        total += value_in_base

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


@log_action("BUY", verbose=True)
def buy_currency(
    user_id: int,
    currency_code: str,
    amount: float,
) -> dict[str, Any]:
    code = validate_currency_code(currency_code)
    amt = _validate_amount_positive(amount)

    base = validate_currency_code(
        SettingsLoader().get("BASE_CURRENCY", "USD")
    )

    wallets = _load_user_portfolio(user_id)
    before = wallets.get(code, 0.0)

    wallet = Wallet(currency_code=code, balance=before)
    wallet.deposit(amt)
    after = wallet.balance

    _save_user_wallet_balance(user_id, code, after)

    rate = get_rate_with_cache(code, base)["rate"]

    return {
        "currency": code,
        "amount": amt,
        "base": base,
        "rate": rate,
        "before": before,
        "after": after,
        "value_in_base": amt * rate,
    }



@log_action("SELL", verbose=True)
def sell_currency(
    user_id: int,
    currency_code: str,
    amount: float,
) -> dict[str, Any]:
    code = validate_currency_code(currency_code)
    amt = _validate_amount_positive(amount)

    base = validate_currency_code(SettingsLoader().get("BASE_CURRENCY", "USD"))

    wallets = _load_user_portfolio(user_id)

    if code not in wallets:
        raise ValueError(
            f"У вас нет кошелька '{code}'. Добавьте валюту: "
            "она создаётся автоматически при первой покупке."
        )

    before = wallets[code]

    wallet = Wallet(currency_code=code, balance=before)
    wallet.withdraw(amt)  
    after = wallet.balance

    _save_user_wallet_balance(user_id, code, after)

    rate = get_rate_with_cache(code, base)["rate"]
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
        "value_in_base": revenue,
    }


def _parse_iso_dt(value: str) -> datetime | None:
    if not isinstance(value, str) or value.strip() == "":
        return None

    s = value.strip()

    # Приводим ISO с Z к ISO с +00:00
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None

    # Если нет tzinfo — считаем, что это UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt


def _is_fresh(updated_at_iso: str, max_age_seconds: int = 300) -> bool:
    dt = _parse_iso_dt(updated_at_iso)
    if dt is None:
        return False
    age = (datetime.now(timezone.utc) - dt).total_seconds()
    return age <= max_age_seconds


def get_rate_with_cache(
    from_code: str,
    to_code: str,
    max_age_seconds: int | None = None,
) -> dict[str, Any]:
    f = _normalize_currency_code(from_code)
    t = _normalize_currency_code(to_code)

    if f == t:
        now_ts = datetime.now().isoformat(timespec="seconds")
        return {
            "from": f, 
            "to": t, 
            "rate": 1.0, 
            "updated_at": now_ts, 
            "reverse_rate": 1.0,
        }

    if max_age_seconds is None:
        max_age_seconds = int(SettingsLoader().get("RATES_TTL_SECONDS", 300))

    pair = f"{f}_{t}"
    reverse_pair = f"{t}_{f}"

    snapshot = _load_rates()
    pairs = snapshot.get("pairs") if isinstance(snapshot, dict) else None
    
    if isinstance(pairs, dict):
        rates = pairs
    elif isinstance(snapshot, dict):
        rates = snapshot
    else:
        rates = {}    
    
    last_refresh = snapshot.get("last_refresh") if isinstance(snapshot, dict) else None

    def _extract_ok(payload: Any) -> tuple[float, str] | None:
        if not isinstance(payload, dict):
            return None
        rate_val = payload.get("rate")
        upd = payload.get("updated_at") or last_refresh
        if not isinstance(rate_val, (int, float)) or float(rate_val) <= 0:
            return None
        if not isinstance(upd, str) or not _is_fresh(
            upd, 
            max_age_seconds=max_age_seconds
        ):
            return None
        return float(rate_val), upd

    direct = _extract_ok(rates.get(pair))
    if direct is not None:
        rate_val, upd = direct
        return {
            "from": f,
            "to": t,
            "rate": rate_val,
            "updated_at": upd,
            "reverse_rate": 1.0 / rate_val,
        }

    rev = _extract_ok(rates.get(reverse_pair))
    if rev is not None:
        rate_rev, upd = rev
        rate_val = 1.0 / rate_rev
        return {
            "from": f,
            "to": t,
            "rate": rate_val,
            "updated_at": upd,
            "reverse_rate": rate_rev,
        }

    raise ApiRequestError(
        f"Курс {f}→{t} отсутствует или устарел. "
        "Выполните 'update-rates' для обновления кеша."
    )


def get_rate(from_code: str, to_code: str) -> dict[str, Any]:
    f = validate_currency_code(from_code)
    t = validate_currency_code(to_code)

    ttl = int(SettingsLoader().get("RATES_TTL_SECONDS", 300))
    return get_rate_with_cache(from_code=f, to_code=t, max_age_seconds=ttl)