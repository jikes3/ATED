from __future__ import annotations

import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.getenv("OPENHEMS_DB_PATH", "/data/openhems.db"))


def init_database() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        db.execute(
            "INSERT OR REPLACE INTO metadata(key, value) VALUES('schema_version', '2')"
        )
    from .registry import RegistryStore

    RegistryStore(DB_PATH).init()
