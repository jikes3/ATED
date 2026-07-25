"""Append-only historian for ATED Core."""
from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterable
from datetime import date, datetime
from functools import partial
import json
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant, State
from homeassistant.util import dt as dt_util

from .const import (
    DATA_DIRECTORY,
    INVALID_RULES,
    QUALITY_INVALID,
    QUALITY_MISSING,
    QUALITY_VALUES,
    QUALITY_VERIFIED,
    SCHEMA_VERSION,
)

UpdateListener = Callable[[], None]


class AtedHistorian:
    """Write immutable JSONL records and expose runtime diagnostics."""

    def __init__(self, hass: HomeAssistant, entity_ids: Iterable[str]) -> None:
        self.hass = hass
        self.entity_ids = tuple(dict.fromkeys(entity_ids))
        self.base_path = Path(hass.config.path(DATA_DIRECTORY))

        self.records_today = 0
        self.last_record_at: datetime | None = None
        self.last_snapshot_at: datetime | None = None
        self.last_error: str | None = None
        self.write_errors = 0
        self.quality_counts = {quality: 0 for quality in QUALITY_VALUES}

        self._counter_day: date | None = None
        self._write_lock = asyncio.Lock()
        self._listeners: set[UpdateListener] = set()

    async def async_initialize(self) -> None:
        """Create storage and initialize today's diagnostics from disk."""
        await self.hass.async_add_executor_job(
            partial(self.base_path.mkdir, parents=True, exist_ok=True)
        )
        await self.hass.async_add_executor_job(self._load_today_stats_sync)
        self._notify_listeners()

    def async_add_update_listener(self, listener: UpdateListener) -> Callable[[], None]:
        """Register a diagnostic entity listener."""
        self._listeners.add(listener)

        def remove_listener() -> None:
            self._listeners.discard(listener)

        return remove_listener

    def _notify_listeners(self) -> None:
        for listener in tuple(self._listeners):
            listener()

    def _quality(self, entity_id: str, state: State) -> tuple[str, Any]:
        """Return quality and normalized value while preserving raw data."""
        raw = state.state
        if raw in ("unknown", "unavailable", ""):
            return QUALITY_MISSING, None

        try:
            normalized: Any = float(raw)
        except (TypeError, ValueError):
            normalized = raw

        rule = INVALID_RULES.get(entity_id)
        if rule and "equals" in rule:
            try:
                if float(raw) == float(rule["equals"]):
                    return QUALITY_INVALID, None
            except (TypeError, ValueError):
                pass

        return QUALITY_VERIFIED, normalized

    def build_record(
        self,
        entity_id: str,
        state: State,
        record_type: str,
        trigger: str,
    ) -> dict[str, Any]:
        """Build one versioned state record."""
        quality, normalized = self._quality(entity_id, state)
        now = dt_util.utcnow()
        return {
            "schema_version": SCHEMA_VERSION,
            "record_type": record_type,
            "timestamp": now.isoformat(),
            "entity_id": entity_id,
            "raw_state": state.state,
            "normalized_value": normalized,
            "unit": state.attributes.get("unit_of_measurement"),
            "quality": quality,
            "trigger": trigger,
            "last_changed": state.last_changed.isoformat(),
            "last_updated": state.last_updated.isoformat(),
            "attributes": dict(state.attributes),
        }

    async def async_log_state(
        self,
        entity_id: str,
        state: State,
        *,
        trigger: str = "state_changed",
    ) -> None:
        """Append one state record."""
        await self._async_append([self.build_record(entity_id, state, "state", trigger)])

    async def async_log_snapshot(self) -> None:
        """Append a point-in-time snapshot of all configured entities."""
        now = dt_util.utcnow()
        values: dict[str, Any] = {}
        snapshot_quality = {quality: 0 for quality in QUALITY_VALUES}

        for entity_id in self.entity_ids:
            state = self.hass.states.get(entity_id)
            if state is None:
                quality, normalized, raw_state, unit = (
                    QUALITY_MISSING,
                    None,
                    None,
                    None,
                )
            else:
                quality, normalized = self._quality(entity_id, state)
                raw_state = state.state
                unit = state.attributes.get("unit_of_measurement")

            snapshot_quality[quality] += 1
            values[entity_id] = {
                "raw_state": raw_state,
                "normalized_value": normalized,
                "unit": unit,
                "quality": quality,
            }

        record = {
            "schema_version": SCHEMA_VERSION,
            "record_type": "snapshot",
            "timestamp": now.isoformat(),
            "entity_count": len(self.entity_ids),
            "quality_summary": snapshot_quality,
            "values": values,
        }
        await self._async_append([record])
        self.last_snapshot_at = now
        self.quality_counts = snapshot_quality
        self._notify_listeners()

    async def async_log_initial_states(self) -> None:
        """Capture current values immediately after setup."""
        records = []
        for entity_id in self.entity_ids:
            state = self.hass.states.get(entity_id)
            if state is not None:
                records.append(self.build_record(entity_id, state, "state", "initial"))
        if records:
            await self._async_append(records)
        await self.async_log_snapshot()

    async def async_archive_size(self) -> int:
        """Return total historian archive size in bytes."""
        return await self.hass.async_add_executor_job(self._archive_size_sync)

    async def _async_append(self, records: list[dict[str, Any]]) -> None:
        """Serialize writes and perform blocking I/O in executor."""
        if not records:
            return

        async with self._write_lock:
            try:
                await self.hass.async_add_executor_job(self._append_sync, records)
            except OSError as err:
                self.write_errors += 1
                self.last_error = f"{type(err).__name__}: {err}"
                self._notify_listeners()
                raise

            self._reset_daily_counters_if_needed()
            self.records_today += len(records)
            self.last_record_at = dt_util.utcnow()
            self.last_error = None
            self._notify_listeners()

    def _reset_daily_counters_if_needed(self) -> None:
        today = dt_util.utcnow().date()
        if self._counter_day != today:
            self._counter_day = today
            self.records_today = 0

    def _today_path(self) -> Path:
        day = dt_util.utcnow().date().isoformat()
        return self.base_path / f"ated-{day}.jsonl"

    def _append_sync(self, records: list[dict[str, Any]]) -> None:
        path = self._today_path()
        with path.open("a", encoding="utf-8") as handle:
            for record in records:
                handle.write(
                    json.dumps(
                        record,
                        ensure_ascii=False,
                        separators=(",", ":"),
                        default=str,
                    )
                    + "\n"
                )
            handle.flush()

    def _load_today_stats_sync(self) -> None:
        """Restore record count and timestamps after HA restart."""
        self._counter_day = dt_util.utcnow().date()
        path = self._today_path()
        if not path.exists():
            return

        count = 0
        last_record: datetime | None = None
        last_snapshot: datetime | None = None
        latest_quality: dict[str, int] | None = None

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
                        last_record = datetime.fromisoformat(timestamp)
                    except (TypeError, ValueError):
                        pass
                if record.get("record_type") == "snapshot":
                    last_snapshot = last_record
                    summary = record.get("quality_summary")
                    if isinstance(summary, dict):
                        latest_quality = {
                            quality: int(summary.get(quality, 0))
                            for quality in QUALITY_VALUES
                        }

        self.records_today = count
        self.last_record_at = last_record
        self.last_snapshot_at = last_snapshot
        if latest_quality is not None:
            self.quality_counts = latest_quality

    def _archive_size_sync(self) -> int:
        return sum(
            path.stat().st_size
            for path in self.base_path.glob("ated-*.jsonl")
            if path.is_file()
        )
