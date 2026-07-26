"""Historian Health Core for ATED."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import time
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

REFRESH_INTERVAL_SECONDS = 300


@dataclass(slots=True)
class HistorianHealthSnapshot:
    """Cached health information about the ATED historian."""

    refreshed_at: datetime
    archive_size_bytes: int = 0
    total_records: int = 0
    archive_days: int = 0
    first_record_at: datetime | None = None
    last_record_at: datetime | None = None
    last_snapshot_at: datetime | None = None
    daily_growth_bytes: float = 0.0
    disk_total_bytes: int = 0
    disk_used_bytes: int = 0
    disk_free_bytes: int = 0
    disk_used_percent: float = 0.0
    estimated_days_remaining: float | None = None
    unreadable_lines: int = 0


class HistorianHealthMonitor:
    """Collect and cache disk and archive diagnostics."""

    def __init__(self, hass: HomeAssistant, base_path: Path) -> None:
        self.hass = hass
        self.base_path = base_path
        self.started_at = dt_util.utcnow()
        self._last_refresh_monotonic = 0.0
        self._snapshot = HistorianHealthSnapshot(refreshed_at=self.started_at)

    @property
    def snapshot(self) -> HistorianHealthSnapshot:
        return self._snapshot

    @property
    def uptime_seconds(self) -> int:
        return max(0, int((dt_util.utcnow() - self.started_at).total_seconds()))

    async def async_refresh(self, *, force: bool = False) -> HistorianHealthSnapshot:
        """Refresh cached diagnostics at most once per five minutes."""
        now_mono = time.monotonic()
        if (
            not force
            and self._last_refresh_monotonic
            and now_mono - self._last_refresh_monotonic < REFRESH_INTERVAL_SECONDS
        ):
            return self._snapshot

        self._snapshot = await self.hass.async_add_executor_job(self._scan_sync)
        self._last_refresh_monotonic = now_mono
        return self._snapshot

    def _scan_sync(self) -> HistorianHealthSnapshot:
        """Scan JSONL files and filesystem usage outside the event loop."""
        refreshed_at = datetime.now(timezone.utc)
        self.base_path.mkdir(parents=True, exist_ok=True)

        files = sorted(self.base_path.glob("ated-*.jsonl"))
        archive_size = 0
        total_records = 0
        first_record: datetime | None = None
        last_record: datetime | None = None
        last_snapshot: datetime | None = None
        unreadable_lines = 0
        file_sizes: list[int] = []

        for path in files:
            try:
                size = path.stat().st_size
            except OSError:
                continue

            archive_size += size
            file_sizes.append(size)

            try:
                with path.open("r", encoding="utf-8") as handle:
                    for line in handle:
                        if not line.strip():
                            continue
                        total_records += 1
                        try:
                            record: dict[str, Any] = json.loads(line)
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            unreadable_lines += 1
                            continue

                        timestamp = _parse_timestamp(record.get("timestamp"))
                        if timestamp is not None:
                            if first_record is None or timestamp < first_record:
                                first_record = timestamp
                            if last_record is None or timestamp > last_record:
                                last_record = timestamp
                            if record.get("record_type") == "snapshot":
                                if last_snapshot is None or timestamp > last_snapshot:
                                    last_snapshot = timestamp
            except OSError:
                unreadable_lines += 1

        archive_days = len(files)
        daily_growth = (
            sum(file_sizes) / len(file_sizes)
            if file_sizes
            else 0.0
        )

        usage = shutil.disk_usage(self.base_path)
        used = usage.total - usage.free
        used_percent = round((used / usage.total) * 100, 1) if usage.total else 0.0
        estimated_days = (
            usage.free / daily_growth
            if daily_growth > 0
            else None
        )

        return HistorianHealthSnapshot(
            refreshed_at=refreshed_at,
            archive_size_bytes=archive_size,
            total_records=total_records,
            archive_days=archive_days,
            first_record_at=first_record,
            last_record_at=last_record,
            last_snapshot_at=last_snapshot,
            daily_growth_bytes=daily_growth,
            disk_total_bytes=usage.total,
            disk_used_bytes=used,
            disk_free_bytes=usage.free,
            disk_used_percent=used_percent,
            estimated_days_remaining=estimated_days,
            unreadable_lines=unreadable_lines,
        )


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
