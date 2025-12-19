from __future__ import annotations

import shlex

from valutatrade_hub.core.usecases import (
    build_portfolio_report,
    buy_currency,
    login_user,
    register_user,
    sell_currency,
)


def _get_flag_value(tokens: list[str], flag: str) -> str | None:
    # Ищем: --username alice  -> вернём alice
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

                # Форматирование похоже на пример
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
                    base_currency="USD",
                )
            except ValueError as exc:
                print(str(exc))
                continue
            except TypeError as exc:
                print(str(exc))
                continue

            cur = result["currency"]
            base = result["base"]
            rate = result["rate"]
            before = result["before"]
            after = result["after"]
            cost = result["cost"]
            amt = result["amount"]

            amt_str = f"{amt:.4f}" if cur in {"BTC", "ETH"} else f"{amt:.2f}"
            before_str = f"{before:.4f}" if cur in {"BTC", "ETH"} else f"{before:.2f}"
            after_str = f"{after:.4f}" if cur in {"BTC", "ETH"} else f"{after:.2f}"

            print(
                f"Покупка выполнена: {amt_str} {cur} "
                f"по курсу {rate:,.2f} {base}/{cur}"
            )
            print("Изменения в портфеле:")
            print(f"- {cur}: было {before_str} → стало {after_str}")
            print(f"Оценочная стоимость покупки: {cost:,.2f} {base}")
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
                    base_currency="USD",
                )
            except ValueError as exc:
                print(str(exc))
                continue
            except TypeError as exc:
                print(str(exc))
                continue

            cur = result["currency"]
            base = result["base"]
            rate = result["rate"]
            before = result["before"]
            after = result["after"]
            revenue = result["revenue"]
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




        print(f"Неизвестная команда: {command}")
