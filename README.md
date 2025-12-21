# ValutaTrade Hub

Консольное приложение-симулятор валютного кошелька: регистрация пользователей, портфель валют, покупка/продажа, получение курса с кешированием.

**Установка**
```bash
make install
```

**Запуск**
```bash
make project
```

## Команды CLI
**Регистрация**
```bash
register --username alice --password 1234
```

**Логин**
```bash
login --username alice --password 1234
```

**Показать портфель**
```bash
show-portfolio
show-portfolio --base USD
```

**Купить валюту**
```bash
buy --currency BTC --amount 0.01
```

**Продать валюту**
```bash
sell --currency BTC --amount 0.005
```

**Получить курс**
```bash
get-rate --from USD --to BTC
```

## Parser commands (обновление и просмотр кеша курсов)

Проект использует `Parser Service`, который умеет обновлять локальный кеш курсов валют и показывать его содержимое.

### update-rates
Запускает немедленное обновление курсов и записывает их в `data/rates.json`
(а также историю в `data/exchange_rates.json`).

**Аргументы:**
- `--source <str>` (опционально) — обновить данные только из указанного источника:
  - `coingecko`
  - `exchangerate`
По умолчанию обновляются все источники.

**Примеры:**
```bash
update-rates
update-rates --source coingecko
update-rates --source exchangerate
```

**Ожидаемый вывод (пример):**
```bash
INFO: Starting rates update...
INFO: Fetching from CoinGecko... OK (3 rates)
INFO: Fetching from ExchangeRate-API... OK (3 rates)
INFO: Writing 6 rates to data/rates.json...
Update successful. Total rates updated: 6. Last refresh: 2025-12-21T10:46:09Z
```

**show-rates**

Показывает список актуальных курсов из локального кеша с фильтрацией.

Аргументы:
```bash
--currency <str> # показать курс только для указанной валюты (например, BTC)

--top <int> # показать N самых дорогих валют (по значению курса)

--base <str> # показать курсы относительно указанной базы (например, EUR)
```

## Demo

Запись работы CLI (asciinema):
[![asciinema demo](https://asciinema.org/a/od3gIbFoyPU9nb89wWSZzxekp.svg)](https://asciinema.org/a/od3gIbFoyPU9nb89wWSZzxekp)


В демо показано:
- register → login → buy/sell → show-portfolio → get-rate
- update-rates → show-rates
- обработка ошибок (пустой кеш, недостаточно средств, неизвестная валюта)