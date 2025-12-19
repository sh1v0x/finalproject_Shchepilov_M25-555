from __future__ import annotations

import functools
import logging
from datetime import datetime
from typing import Any, Callable, TypeVar, cast

T = TypeVar("T")


def log_action(
    action: str,
    *,
    verbose: bool = False,
) -> Callable[[Callable[..., T]], Callable[..., T]]:

    """
    Декоратор логирования доменных операций.

    Логируем на INFO:
      timestamp (ISO), action, username/user_id, currency_code, amount, rate, base,
      result (OK/ERROR), error_type/error_message.
    Исключения НЕ глотаем — пробрасываем дальше.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        logger = logging.getLogger("valutatrade.actions")

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            ts = datetime.now().isoformat(timespec="seconds")

            # Достаём общие поля из kwargs 
            user_id = kwargs.get("user_id")
            username = kwargs.get("username")
            currency_code = kwargs.get("currency_code")
            amount = kwargs.get("amount")
            base_currency = kwargs.get("base_currency")

            try:
                result = func(*args, **kwargs)

                # Попробуем достать rate/base из результата
                rate = None
                base = base_currency
                extra = ""

                if isinstance(result, dict):
                    rate = result.get("rate")
                    base = result.get("base", base)
                    if verbose:
                        before = result.get("before")
                        after = result.get("after")
                        if before is not None and after is not None:
                            extra = f" before={before} after={after}"

                who = f"user='{username}'" if username else f"user_id={user_id}"
                msg = (
                    f"{ts} {action} {who} currency='{currency_code}' amount={amount} "
                    f"rate={rate} base='{base}' result=OK{extra}"
                )
                logger.info(msg)
                return cast(T, result)

            except Exception as exc:  # noqa: BLE001
                who = f"user='{username}'" if username else f"user_id={user_id}"
                err_type = type(exc).__name__
                err_msg = str(exc)
                msg = (
                    f"{ts} {action} {who} currency='{currency_code}' amount={amount} "
                    f"result=ERROR error_type={err_type} error_message='{err_msg}'"
                )
                logger.info(msg)
                raise

        return wrapper

    return decorator
