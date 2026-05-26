from __future__ import annotations

import os

from versa.store.base import Store
from versa.store.memory import InMemoryStore
from versa.store.sqlite import SQLiteStore


def resolve_db_path(db_path: str | None) -> str | None:
    if db_path:
        return db_path
    env_path = os.environ.get("VERSA_DB_PATH", "").strip()
    return env_path or None


def make_store(db_path: str | None) -> Store:
    resolved = resolve_db_path(db_path)
    if resolved:
        return SQLiteStore(resolved)
    return InMemoryStore()
