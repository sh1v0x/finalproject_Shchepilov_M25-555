# ValutaTrade Hub

Консольное приложение-симулятор валютного кошелька: регистрация пользователей, портфель валют, покупка/продажа, получение курса с кешированием.

## Установка
```bash
make install
```

**Запуск**
```bash
make project
```

**Команды CLI**
Регистрация
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