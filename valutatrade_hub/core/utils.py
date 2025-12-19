from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any


def project_root() -> Path:
    # core/utils.py -> core -> valutatrade_hub -> PROJECT_ROOT
    return Path(__file__).resolve().parents[2]


def data_dir() -> Path:
    return project_root() / "data"


def ensure_data_dir() -> None:
    data_dir().mkdir(parents=True, exist_ok=True)


def load_json(path: Path, default: Any) -> Any:
    ensure_data_dir()
    if not path.exists():
        return default
    text = path.read_text(encoding="utf-8").strip()
    if text == "":
        return default
    return json.loads(text)


def save_json(path: Path, data: Any) -> None:
    ensure_data_dir()
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def normalize_username(username: str) -> str:
    if not isinstance(username, str):
        raise TypeError("Username must be str")
    value = username.strip()
    if value == "":
        raise ValueError("Username cannot be empty")
    return value


def validate_password(password: str) -> None:
    if not isinstance(password, str):
        raise TypeError("Password must be str")
    if len(password) < 4:
        raise ValueError("Password must be at least 4 characters long")


def generate_salt(length: int = 8) -> str:
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def hash_password(password: str, salt: str) -> str:
    raw = (password + salt).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")
