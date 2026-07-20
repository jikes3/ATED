from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from .models import Device, EntityMapping


class RegistryStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def init(self) -> None:
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS devices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    device_type TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS entity_mappings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_key TEXT NOT NULL,
                    function TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    source TEXT NOT NULL DEFAULT 'manual',
                    confidence INTEGER NOT NULL DEFAULT 100,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(device_key, function),
                    FOREIGN KEY(device_key) REFERENCES devices(key) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_entity_mappings_entity_id
                    ON entity_mappings(entity_id);
                """
            )

    def upsert_device(self, device: Device) -> Device:
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO devices(key, name, device_type, enabled)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    name=excluded.name,
                    device_type=excluded.device_type,
                    enabled=excluded.enabled,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (device.key, device.name, device.device_type, int(device.enabled)),
            )
            row = db.execute("SELECT * FROM devices WHERE key = ?", (device.key,)).fetchone()
        assert row is not None
        return self._device_from_row(row)

    def upsert_mapping(self, mapping: EntityMapping) -> EntityMapping:
        with self._connect() as db:
            exists = db.execute("SELECT 1 FROM devices WHERE key = ?", (mapping.device_key,)).fetchone()
            if exists is None:
                raise ValueError(f"Neznámé zařízení: {mapping.device_key}")
            db.execute(
                """
                INSERT INTO entity_mappings(device_key, function, entity_id, source, confidence)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(device_key, function) DO UPDATE SET
                    entity_id=excluded.entity_id,
                    source=excluded.source,
                    confidence=excluded.confidence,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (mapping.device_key, mapping.function, mapping.entity_id, mapping.source, mapping.confidence),
            )
            row = db.execute(
                "SELECT * FROM entity_mappings WHERE device_key = ? AND function = ?",
                (mapping.device_key, mapping.function),
            ).fetchone()
        assert row is not None
        return self._mapping_from_row(row)

    def list_devices(self) -> list[dict[str, Any]]:
        with self._connect() as db:
            devices = db.execute("SELECT * FROM devices ORDER BY device_type, name").fetchall()
            mappings = db.execute("SELECT * FROM entity_mappings ORDER BY device_key, function").fetchall()
        by_device: dict[str, list[dict[str, Any]]] = {}
        for row in mappings:
            mapping = self._mapping_from_row(row).to_dict()
            by_device.setdefault(mapping["device_key"], []).append(mapping)
        result: list[dict[str, Any]] = []
        for row in devices:
            device = self._device_from_row(row).to_dict()
            device["mappings"] = by_device.get(device["key"], [])
            result.append(device)
        return result

    def get_mapping(self, device_key: str, function: str) -> EntityMapping | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM entity_mappings WHERE device_key = ? AND function = ?",
                (device_key, function),
            ).fetchone()
        return self._mapping_from_row(row) if row else None

    def delete_mapping(self, device_key: str, function: str) -> bool:
        with self._connect() as db:
            cursor = db.execute(
                "DELETE FROM entity_mappings WHERE device_key = ? AND function = ?",
                (device_key, function),
            )
        return cursor.rowcount > 0

    @staticmethod
    def _device_from_row(row: sqlite3.Row) -> Device:
        return Device(
            id=int(row["id"]),
            key=str(row["key"]),
            name=str(row["name"]),
            device_type=str(row["device_type"]),
            enabled=bool(row["enabled"]),
        )

    @staticmethod
    def _mapping_from_row(row: sqlite3.Row) -> EntityMapping:
        return EntityMapping(
            id=int(row["id"]),
            device_key=str(row["device_key"]),
            function=str(row["function"]),
            entity_id=str(row["entity_id"]),
            source=str(row["source"]),
            confidence=int(row["confidence"]),
        )
