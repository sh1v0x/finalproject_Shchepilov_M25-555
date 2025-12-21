from __future__ import annotations

import shlex
from pathlib import Path

from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from valutatrade_hub.core.usecases import (
    build_portfolio_report,
    buy_currency,
    get_rate,
    login_user,
    register_user,
    sell_currency,
)
from valutatrade_hub.parser_service.api_clients import (
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.storage import RatesStorage, load_snapshot
from valutatrade_hub.parser_service.updater import RatesUpdater


def _get_flag_value(tokens: list[str], flag: str) -> str | None:
    try:
        idx = tokens.index(flag)
    except ValueError:
        return None
    if idx + 1 >= len(tokens):
        return None
    return tokens[idx + 1]


def run_cli() -> None:
    print("ValutaTrade Hub CLI")
    print("Введите команду (register, login) или 'exit' для выхода.")


    current_user_id: int | None = None
    current_username: str | None = None



    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nВыход.")
            return

        if line == "":
            continue

        if line in {"exit", "quit"}:
            print("Выход.")
            return

        tokens = shlex.split(line)
        command = tokens[0]

        if command == "register":
            username = _get_flag_value(tokens, "--username")
            password = _get_flag_value(tokens, "--password")

            if not username or not password:
                print("Ошибка: используйте register --username <str> --password <str>")
                continue

            try:
                user_id, uname = register_user(username=username, password=password)
            except ValueError as exc:
                print(str(exc))
                continue
            except TypeError as exc:
                print(str(exc))
                continue

            print(
                f"Пользователь '{uname}' зарегистрирован (id={user_id}). "
                f"Войдите: login --username {uname} --password ****"
            )
            continue

        if command == "login":
            username = _get_flag_value(tokens, "--username")
            password = _get_flag_value(tokens, "--password")

            if not username or not password:
                print("Ошибка: используйте login --username <str> --password <str>")
                continue

            try:
                user_id, uname = login_user(username=username, password=password)
            except ValueError as exc:
                print(str(exc))
                continue
            except TypeError as exc:
                print(str(exc))
                continue

            current_user_id = user_id  
            current_username = uname  

            print(f"Вы вошли как '{uname}'")
            continue

        if command == "show-portfolio":
            if current_user_id is None or current_username is None:
                print("Сначала выполните login")
                continue

            base = _get_flag_value(tokens, "--base") or "USD"

            try:
                report = build_portfolio_report(current_user_id, base_currency=base)
            except ValueError as exc:
                print(str(exc))
                continue
            except TypeError as exc:
                print(str(exc))
                continue

            base_code = report["base"]
            items = report["items"]
            total = report["total"]

            print(f"Портфель пользователя '{current_username}' (база: {base_code}):")

            if not items:
                print("Кошельков нет")
                continue

            for item in items:
                code = item["currency_code"]
                bal = item["balance"]
                val = item["value_in_base"]

                if code in {"BTC", "ETH"}:
                    bal_str = f"{bal:.4f}"
                else:
                    bal_str = f"{bal:.2f}"

                print(f"- {code}: {bal_str}  → {val:,.2f} {base_code}")

            print("---------------------------------")
            print(f"ИТОГО: {total:,.2f} {base_code}")
            continue

        if command == "buy":
            if current_user_id is None or current_username is None:
                print("Сначала выполните login")
                continue

            currency = _get_flag_value(tokens, "--currency")
            amount_str = _get_flag_value(tokens, "--amount")

            if not currency or not amount_str:
                print("Ошибка: используйте buy --currency <str> --amount <float>")
                continue

            try:
                amount = float(amount_str)
            except ValueError:
                print("'amount' должен быть положительным числом")
                continue

            try:
                result = buy_currency(
                    user_id=current_user_id,
                    currency_code=currency,
                    amount=amount,
                )
            except CurrencyNotFoundError as exc:
                print(str(exc))
                print(
                    "Подсказка: используйте get-rate или"
                    "проверьте код валюты (USD/EUR/BTC/ETH/RUB)."
                )
                continue
            except ApiRequestError as exc:
                print(str(exc))
                print("Подсказка: повторите попытку позже.")
                continue
            except (ValueError, TypeError) as exc:
                print(str(exc))
                continue

            cur = result["currency"]
            amt = result["amount"]
            base = result["base"]
            rate = result["rate"]
            before = result["before"]
            after = result["after"]
            value = result["value_in_base"]

            amt_str = f"{amt:.4f}" if cur in {"BTC", "ETH"} else f"{amt:.2f}"
            before_str = f"{before:.4f}" if cur in {"BTC", "ETH"} else f"{before:.2f}"
            after_str = f"{after:.4f}" if cur in {"BTC", "ETH"} else f"{after:.2f}"

            print(
                f"Покупка выполнена: {amt_str} {cur} "
                f"по курсу {rate:,.2f} {base}/{cur}"
            )
            print("Изменения в портфеле:")
            print(f"- {cur}: было {before_str} → стало {after_str}")
            print(f"Оценочная стоимость покупки: {value:,.2f} {base}")
            continue

        
        if command == "sell":
            if current_user_id is None or current_username is None:
                print("Сначала выполните login")
                continue

            currency = _get_flag_value(tokens, "--currency")
            amount_str = _get_flag_value(tokens, "--amount")

            if not currency or not amount_str:
                print("Ошибка: используйте sell --currency <str> --amount <float>")
                continue

            try:
                amount = float(amount_str)
            except ValueError:
                print("'amount' должен быть положительным числом")
                continue

            try:
                result = sell_currency(
                    user_id=current_user_id,
                    currency_code=currency,
                    amount=amount,
                )
            except InsufficientFundsError as exc:
                print(str(exc))
                continue
            except CurrencyNotFoundError as exc:
                print(str(exc))
                print("Подсказка: проверьте код валюты (USD/EUR/BTC/ETH/RUB).")
                continue
            except ApiRequestError as exc:
                print(str(exc))
                print("Подсказка: повторите попытку позже.")
                continue
            except (ValueError, TypeError) as exc:
                print(str(exc))
                continue

            cur = result["currency"]
            base = result["base"]
            rate = result["rate"]
            before = result["before"]
            after = result["after"]
            revenue = result["value_in_base"]
            amt = result["amount"]

            amt_str = f"{amt:.4f}" if cur in {"BTC", "ETH"} else f"{amt:.2f}"
            before_str = f"{before:.4f}" if cur in {"BTC", "ETH"} else f"{before:.2f}"
            after_str = f"{after:.4f}" if cur in {"BTC", "ETH"} else f"{after:.2f}"

            print(
                f"Продажа выполнена: {amt_str} {cur} "
                f"по курсу {rate:,.2f} {base}/{cur}"
            )
            print("Изменения в портфеле:")
            print(f"- {cur}: было {before_str} → стало {after_str}")
            print(f"Оценочная выручка: {revenue:,.2f} {base}")
            continue

        if command == "get-rate":
            from_code = _get_flag_value(tokens, "--from")
            to_code = _get_flag_value(tokens, "--to")

            if not from_code or not to_code:
                print("Ошибка: используйте get-rate --from <str> --to <str>")
                continue

            try:
                info = get_rate(from_code=from_code, to_code=to_code)
            except CurrencyNotFoundError as exc:
                print(str(exc))
                print("Подсказка: проверьте коды валют (USD/EUR/BTC/ETH/RUB).")
                continue
            except ApiRequestError:
                print(
                    f"Курс {from_code.upper()}→{to_code.upper()} недоступен. "
                    "Повторите попытку позже."
                )
                continue
            except (ValueError, TypeError) as exc:
                print(str(exc))
                continue

            from_cur = info["from"]
            to_cur = info["to"]
            rate = info["rate"]
            updated_at = info["updated_at"]
            reverse = info.get("reverse_rate")

            print(
                f"Курс {from_cur}→{to_cur}: {rate:.8f} "
                f"(обновлено: {updated_at})"
            )

            if reverse is not None:
                print(f"Обратный курс {to_cur}→{from_cur}: {reverse:,.2f}")

            continue

        if command == "update-rates":
            source = _get_flag_value(tokens, "--source")
            if source is not None:
                source = source.strip().lower()

            clients_all = {
                "CoinGecko": CoinGeckoClient(),
                "ExchangeRate-API": ExchangeRateApiClient(),
            }

            if source is None:
                clients = clients_all
            else:
                if source == "coingecko":
                    clients = {"CoinGecko": clients_all["CoinGecko"]}
                elif source == "exchangerate":
                    clients = {"ExchangeRate-API": clients_all["ExchangeRate-API"]}
                else:
                    print(
                        "Ошибка: используйте"
                        "update-rates --source <coingecko|exchangerate>"
                    )
                    continue

            storage = RatesStorage(
                snapshot_path=Path("data/rates.json"),
                history_path=Path("data/exchange_rates.json"),
            )
            updater = RatesUpdater(clients=clients, storage=storage)

            print("INFO: Starting rates update...")

            try:
                result = updater.run_update()
            except ApiRequestError as exc:
                print(f"ERROR: {exc}")
                print("Update failed. Check logs/parser.log for details.")
                continue

            for src_name, meta in result.sources.items():
                ok = bool(meta.get("ok"))
                if ok:
                    cnt = int(meta.get("count", 0))
                    print(f"INFO: Fetching from {src_name}... OK ({cnt} rates)")
                else:
                    err = meta.get("error", "Unknown error")
                    print(f"ERROR: Failed to fetch from {src_name}: {err}")

            print(f"INFO: Writing {result.updated} rates to data/rates.json...")

            if result.had_errors:
                print(
                    "Update completed with errors. " 
                    "Check logs/parser.log for details."
                )
            else:
                print(
                    f"Update successful. Total rates updated: {result.updated}. "
                    f"Last refresh: {result.last_refresh}"
                )
            continue

        if command == "show-rates":
            # show-rates [--currency BTC] [--top 5] [--base EUR]
            currency = _get_flag_value(tokens, "--currency")
            top_str = _get_flag_value(tokens, "--top")
            base = _get_flag_value(tokens, "--base") or "USD"

            if currency is not None:
                currency = currency.strip().upper()
            base = base.strip().upper()

            top: int | None = None
            if top_str is not None:
                try:
                    top = int(top_str)
                    if top <= 0:
                        raise ValueError
                except ValueError:
                    print("Ошибка: --top должен быть положительным целым числом")
                    continue

            cache_path = Path("data/rates.json")
            if not cache_path.exists():
                print(
                    "Локальный кеш курсов пуст. "
                    "Выполните 'update-rates', чтобы загрузить данные."
                )
                continue

            snap = load_snapshot(cache_path)
            pairs = snap.get("pairs") or {}
            last_refresh = snap.get("last_refresh")

            if not isinstance(pairs, dict) or len(pairs) == 0:
                print(
                    "Локальный кеш курсов пуст." 
                    "Выполните 'update-rates', чтобы загрузить данные."
                )
                continue

            # Преобразуем в список (pair, rate, updated_at)
            rows: list[tuple[str, float, str]] = []
            for pair, payload in pairs.items():
                if not isinstance(pair, str):
                    continue
                if not isinstance(payload, dict):
                    continue
                rate = payload.get("rate")
                updated_at = payload.get("updated_at") or (last_refresh or "")
                if isinstance(rate, (int, float)) and float(rate) > 0:
                    rows.append((pair, float(rate), str(updated_at)))

            # Фильтр по base: оставляем *_BASE
            if base:
                rows = [r for r in rows if r[0].endswith(f"_{base}")]

            # Фильтр по currency: оставляем CURRENCY_*
            if currency:
                rows = [r for r in rows if r[0].startswith(f"{currency}_")]

            if not rows:
                if currency:
                    print(f"Курс для '{currency}' не найден в кеше.")
                else:
                    print(
                        "По заданным фильтрам курсы не найдены. "
                        "Попробуйте изменить --base/--currency "
                        "или обновить кеш через update-rates."
                    )
                continue

            # Сортировки:
            # - если --top: по rate desc
            # - иначе: по имени пары
            if top is not None:
                rows.sort(key=lambda x: x[1], reverse=True)
                rows = rows[:top]
            else:
                rows.sort(key=lambda x: x[0])

            header_ts = last_refresh if isinstance(last_refresh, str) else "unknown"
            print(f"Rates from cache (updated at {header_ts}):")

            for pair, rate, _upd in rows:
                print(f"- {pair}: {rate}")

            continue


        print(f"Неизвестная команда: {command}")
