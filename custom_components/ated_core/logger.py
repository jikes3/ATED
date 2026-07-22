"""Append-only historical data logger for ATED Core."""
from __future__ import annotations

import asyncio
from collections.abc import Iterable
from datetime import datetime
import json
from functools import partial
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant, State
from homeassistant.util import dt as dt_util

from .const import DATA_DIRECTORY, INVALID_RULES, SCHEMA_VERSION


class AtedDataLogger:
    """Write immutable JSONL records for later analysis and migrations."""

    def __init__(self, hass: HomeAssistant, entity_ids: Iterable[str]) -> None:
        self.hass = hass
        self.entity_ids = tuple(dict.fromkeys(entity_ids))
        self.base_path = Path(hass.config.path(DATA_DIRECTORY))
        self.records_today = 0
        self.last_record_at: datetime | None = None
        self._write_lock = asyncio.Lock()

    async def async_initialize(self) -> None:
        """Create data directory."""
        await self.hass.async_add_executor_job(
            partial(self.base_path.mkdir, parents=True, exist_ok=True)
        )

    def _quality(self, entity_id: str, state: State) -> tuple[str, Any]:
        """Return quality and normalized value without destroying raw data."""
        raw = state.state
        if raw in ("unknown", "unavailable", ""):
            return "missing", None

        try:
            normalized: Any = float(raw)
        except (TypeError, ValueError):
            normalized = raw

        rule = INVALID_RULES.get(entity_id)
        if rule and "equals" in rule:
            try:
                if float(raw) == float(rule["equals"]):
                    return "invalid", None
            except (TypeError, ValueError):
                pass

        return "verified", normalized

    def build_record(
        self,
        entity_id: str,
        state: State,
        record_type: str,
        trigger: str,
    ) -> dict[str, Any]:
        """Build a versioned record."""
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
        record = self.build_record(entity_id, state, "state", trigger)
        await self._async_append([record])

    async def async_log_snapshot(self) -> None:
        """Append a point-in-time snapshot of all configured entities."""
        now = dt_util.utcnow()
        values: dict[str, Any] = {}
        for entity_id in self.entity_ids:
            state = self.hass.states.get(entity_id)
            if state is None:
                values[entity_id] = {
                    "raw_state": None,
                    "normalized_value": None,
                    "unit": None,
                    "quality": "missing",
                }
                continue
            quality, normalized = self._quality(entity_id, state)
            values[entity_id] = {
                "raw_state": state.state,
                "normalized_value": normalized,
                "unit": state.attributes.get("unit_of_measurement"),
                "quality": quality,
            }

        record = {
            "schema_version": SCHEMA_VERSION,
            "record_type": "snapshot",
            "timestamp": now.isoformat(),
            "values": values,
        }
        await self._async_append([record])

    async def async_log_initial_states(self) -> None:
        """Capture current values immediately after setup."""
        records = []
        for entity_id in self.entity_ids:
            state = self.hass.states.get(entity_id)
            if state is not None:
                records.append(
                    self.build_record(entity_id, state, "state", "initial")
                )
        if records:
            await self._async_append(records)
        await self.async_log_snapshot()

    async def _async_append(self, records: list[dict[str, Any]]) -> None:
        """Serialize writes and perform blocking I/O in executor."""
        if not records:
            return
        async with self._write_lock:
            await self.hass.async_add_executor_job(self._append_sync, records)
            self.records_today += len(records)
            self.last_record_at = dt_util.utcnow()

    def _append_sync(self, records: list[dict[str, Any]]) -> None:
        """Append records to a daily JSONL file."""
        day = dt_util.utcnow().date().isoformat()
        path = self.base_path / f"ated-{day}.jsonl"
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
