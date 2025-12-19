from __future__ import annotations

import shlex

from valutatrade_hub.core.usecases import login_user, register_user


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

            current_user_id = user_id  # noqa: F841
            current_username = uname  # noqa: F841

            print(f"Вы вошли как '{uname}'")
            continue

        print(f"Неизвестная команда: {command}")
