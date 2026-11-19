from __future__ import annotations

import os
from pathlib import Path

from cryptography.fernet import Fernet

from .db import DATA_DIR


SECRET_DIR = DATA_DIR / "secrets"
SECRET_DIR.mkdir(parents=True, exist_ok=True)
KEY_PATH = SECRET_DIR / "master.key"


def _load_key() -> bytes:
    env_key = os.getenv("AGENTSHOW_MASTER_KEY")
    if env_key:
        return env_key.encode("utf-8")
    if KEY_PATH.exists():
        return KEY_PATH.read_bytes().strip()
    key = Fernet.generate_key()
    KEY_PATH.write_bytes(key)
    try:
        KEY_PATH.chmod(0o600)
    except OSError:
        pass
    return key


_fernet = Fernet(_load_key())


def encrypt_secret(value: str) -> str:
    return _fernet.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str | None) -> str | None:
    if not value:
        return None
    return _fernet.decrypt(value.encode("utf-8")).decode("utf-8")


def mask_secret(value: str) -> str:
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:3]}...{value[-4:]}"

