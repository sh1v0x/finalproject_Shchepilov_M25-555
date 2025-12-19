from __future__ import annotations

import hashlib
import secrets
from datetime import datetime
from typing import Any


class User:
    """
    Пользователь системы.

    Атрибуты (приватные):
      _user_id: int
      _username: str
      _hashed_password: str
      _salt: str
      _registration_date: datetime
    """

    def __init__(
        self,
        user_id: int,
        username: str,
        hashed_password: str,
        salt: str,
        registration_date: datetime,
    ) -> None:
        self._user_id = self._validate_user_id(user_id)
        self._username = self._validate_username(username)
        self._hashed_password = self._validate_non_empty_str(
            hashed_password,
            "hashed_password",
        )
        self._salt = self._validate_non_empty_str(salt, "salt")
        self._registration_date = self._validate_registration_date(registration_date)

    # --------- Public API (по ТЗ) ---------

    def get_user_info(self) -> dict[str, Any]:
        """Возвращает информацию о пользователе без пароля/хэша/соли."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date.isoformat(),
        }

    def change_password(self, new_password: str) -> None:
        """Меняет пароль: генерирует новую соль и сохраняет новый хэш."""
        self._validate_password_plain(new_password)

        new_salt = self._generate_salt()
        new_hash = self._hash_password(new_password, new_salt)

        self._salt = new_salt
        self._hashed_password = new_hash

    def verify_password(self, password: str) -> bool:
        """Проверяет введённый пароль на совпадение."""
        if not isinstance(password, str):
            return False
        candidate_hash = self._hash_password(password, self._salt)
        return candidate_hash == self._hashed_password

    # --------- Getters / setters ---------

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def username(self) -> str:
        return self._username

    @username.setter
    def username(self, value: str) -> None:
        self._username = self._validate_username(value)

    @property
    def hashed_password(self) -> str:
        return self._hashed_password

    @property
    def salt(self) -> str:
        return self._salt

    @property
    def registration_date(self) -> datetime:
        return self._registration_date

    # --------- Internal helpers ---------

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        # Односторонний псевдо-хеш: sha256(password + salt)
        raw = (password + salt).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    @staticmethod
    def _generate_salt(length: int = 8) -> str:
        # Уникальная соль (безопасно для будущих задач)
        alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        return "".join(secrets.choice(alphabet) for _ in range(length))

    @staticmethod
    def _validate_user_id(value: int) -> int:
        if not isinstance(value, int):
            raise TypeError("user_id must be int")
        if value <= 0:
            raise ValueError("user_id must be positive")
        return value

    @staticmethod
    def _validate_username(value: str) -> str:
        if not isinstance(value, str):
            raise TypeError("username must be str")
        cleaned = value.strip()
        if cleaned == "":
            raise ValueError("username cannot be empty")
        return cleaned

    @staticmethod
    def _validate_non_empty_str(value: str, field_name: str) -> str:
        if not isinstance(value, str):
            raise TypeError(f"{field_name} must be str")
        if value.strip() == "":
            raise ValueError(f"{field_name} cannot be empty")
        return value

    @staticmethod
    def _validate_password_plain(value: str) -> None:
        if not isinstance(value, str):
            raise TypeError("password must be str")
        if len(value) < 4:
            raise ValueError("password must be at least 4 characters long")

    @staticmethod
    def _validate_registration_date(value: datetime) -> datetime:
        if not isinstance(value, datetime):
            raise TypeError("registration_date must be datetime")
        return value
    

class Wallet:
    """
    Кошелёк пользователя для одной валюты.
    """

    def __init__(self, currency_code: str, balance: float = 0.0) -> None:
        self.currency_code = currency_code
        self.balance = balance

    # --------- Public API ---------

    def deposit(self, amount: float) -> None:
        """Пополнение баланса."""
        self._validate_amount(amount)
        self.balance += amount

    def withdraw(self, amount: float) -> None:
        """Снятие средств при достаточном балансе."""
        self._validate_amount(amount)
        if amount > self.balance:
            raise ValueError("Insufficient funds")
        self.balance -= amount

    def get_balance_info(self) -> dict[str, float | str]:
        """Возвращает информацию о балансе."""
        return {
            "currency_code": self.currency_code,
            "balance": self.balance,
        }

    # --------- Properties ---------

    @property
    def balance(self) -> float:
        return self._balance

    @balance.setter
    def balance(self, value: float) -> None:
        if not isinstance(value, (int, float)):
            raise TypeError("Balance must be a number")
        if value < 0:
            raise ValueError("Balance cannot be negative")
        self._balance = float(value)

    # --------- Internal helpers ---------

    @staticmethod
    def _validate_amount(amount: float) -> None:
        if not isinstance(amount, (int, float)):
            raise TypeError("Amount must be a number")
        if amount <= 0:
            raise ValueError("Amount must be positive")

