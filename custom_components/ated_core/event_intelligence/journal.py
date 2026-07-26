"""Append-only Event Journal, separated from the Historian archive."""
from __future__ import annotations

import asyncio
import json
from collections.abc import Iterable
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .models import JournalEvent


class EventJournal:
    """Persist explainable actions without changing Historian schema 2."""

    def __init__(self, base_path: Path) -> None:
        self.base_path = base_path
        self._write_lock = asyncio.Lock()
        self.records_today = 0
        self.last_record_at: datetime | None = None
        self.write_errors = 0
        self.last_error: str | None = None
        self._counter_day: date | None = None

    async def async_initialize(self) -> None:
        await asyncio.to_thread(self.base_path.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(self._load_today_stats_sync)

    async def async_append(self, event: JournalEvent) -> None:
        await self.async_append_many((event,))

    async def async_append_many(self, events: Iterable[JournalEvent]) -> None:
        records = [event.to_record() for event in events]
        if not records:
            return
        async with self._write_lock:
            try:
                await asyncio.to_thread(self._append_sync, records)
            except OSError as err:
                self.write_errors += 1
                self.last_error = f"{type(err).__name__}: {err}"
                raise
            self._reset_daily_counter()
            self.records_today += len(records)
            self.last_record_at = datetime.fromisoformat(records[-1]["timestamp"])
            self.last_error = None

    def _today_path(self) -> Path:
        day = datetime.now().astimezone().date().isoformat()
        return self.base_path / f"ated-events-{day}.jsonl"

    def _append_sync(self, records: list[dict[str, Any]]) -> None:
        path = self._today_path()
        with path.open("a", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(
                    record,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    default=str,
                ) + "\n")
            handle.flush()

    def _reset_daily_counter(self) -> None:
        today = datetime.now().astimezone().date()
        if self._counter_day != today:
            self._counter_day = today
            self.records_today = 0

    def _load_today_stats_sync(self) -> None:
        self._counter_day = datetime.now().astimezone().date()
        path = self._today_path()
        if not path.exists():
            return
        count = 0
        last_record_at = None
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                count += 1
                timestamp = record.get("timestamp")
                if timestamp:
                    try:
                        last_record_at = datetime.fromisoformat(timestamp)
                    except (TypeError, ValueError):
                        pass
        self.records_today = count
        self.last_record_at = last_record_at
