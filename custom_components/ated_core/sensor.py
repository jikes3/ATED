"""Diagnostic sensors for ATED Core."""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN, INTEGRATION_VERSION
from .models import AtedRuntimeData


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[AtedRuntimeData],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Historian diagnostic sensors."""
    async_add_entities(
        [
            AtedHistorianStatusSensor(entry),
            AtedRecordsTodaySensor(entry),
            AtedLastRecordSensor(entry),
            AtedLastSnapshotSensor(entry),
            AtedTrackedEntitiesSensor(entry),
            AtedDataQualitySensor(entry),
            AtedArchiveSizeSensor(entry),
            AtedWriteErrorsSensor(entry),
        ],
        update_before_add=True,
    )


class AtedBaseSensor(SensorEntity):
    """Base ATED diagnostic sensor."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry: ConfigEntry[AtedRuntimeData]) -> None:
        self.entry = entry
        self.historian = entry.runtime_data.historian
        self._remove_listener: Callable[[], None] | None = None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="ATED Core",
            manufacturer="ATED",
            model="Historian",
            sw_version=INTEGRATION_VERSION,
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to Historian changes."""
        await super().async_added_to_hass()
        self._remove_listener = self.historian.async_add_update_listener(
            self._handle_historian_update
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from Historian changes."""
        if self._remove_listener is not None:
            self._remove_listener()
            self._remove_listener = None
        await super().async_will_remove_from_hass()

    @callback
    def _handle_historian_update(self) -> None:
        self.async_write_ha_state()


class AtedHistorianStatusSensor(AtedBaseSensor):
    """Overall Historian runtime status."""

    _attr_name = "Historian stav"
    _attr_icon = "mdi:database-check-outline"

    def __init__(self, entry: ConfigEntry[AtedRuntimeData]) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_historian_status"

    @property
    def native_value(self) -> str:
        return "error" if self.historian.last_error else "online"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "last_error": self.historian.last_error,
            "schema_version": 2,
            "storage_directory": str(self.historian.base_path),
        }


class AtedRecordsTodaySensor(AtedBaseSensor):
    """Records written today, including before the latest restart."""

    _attr_name = "Záznamy dnes"
    _attr_icon = "mdi:database-plus"

    def __init__(self, entry: ConfigEntry[AtedRuntimeData]) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_records_today"

    @property
    def native_value(self) -> int:
        return self.historian.records_today


class AtedLastRecordSensor(AtedBaseSensor):
    """Timestamp of the latest successful write."""

    _attr_name = "Poslední záznam"
    _attr_icon = "mdi:clock-check-outline"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, entry: ConfigEntry[AtedRuntimeData]) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_last_record"

    @property
    def native_value(self) -> datetime | None:
        return self.historian.last_record_at


class AtedLastSnapshotSensor(AtedBaseSensor):
    """Timestamp of the latest complete snapshot."""

    _attr_name = "Poslední snapshot"
    _attr_icon = "mdi:camera-timer"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, entry: ConfigEntry[AtedRuntimeData]) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_last_snapshot"

    @property
    def native_value(self) -> datetime | None:
        return self.historian.last_snapshot_at


class AtedTrackedEntitiesSensor(AtedBaseSensor):
    """Number of configured source entities."""

    _attr_name = "Sledované entity"
    _attr_icon = "mdi:format-list-checks"

    def __init__(self, entry: ConfigEntry[AtedRuntimeData]) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_tracked_entities"

    @property
    def native_value(self) -> int:
        return len(self.historian.entity_ids)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"entities": list(self.historian.entity_ids)}


class AtedDataQualitySensor(AtedBaseSensor):
    """Quality score from the latest snapshot."""

    _attr_name = "Kvalita dat"
    _attr_icon = "mdi:shield-check-outline"
    _attr_native_unit_of_measurement = "%"

    def __init__(self, entry: ConfigEntry[AtedRuntimeData]) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_data_quality"

    @property
    def native_value(self) -> int:
        counts = self.historian.quality_counts
        total = sum(counts.values())
        if total == 0:
            return 0
        return round(100 * counts["verified"] / total)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return dict(self.historian.quality_counts)


class AtedArchiveSizeSensor(AtedBaseSensor):
    """Total append-only archive size."""

    _attr_name = "Velikost archivu"
    _attr_icon = "mdi:database-outline"
    _attr_native_unit_of_measurement = "MiB"
    _attr_should_poll = True

    def __init__(self, entry: ConfigEntry[AtedRuntimeData]) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_archive_size"
        self._value = 0.0

    async def async_update(self) -> None:
        size_bytes = await self.historian.async_archive_size()
        self._value = round(size_bytes / 1_048_576, 3)

    @property
    def native_value(self) -> float:
        return self._value


class AtedWriteErrorsSensor(AtedBaseSensor):
    """Number of write failures since HA startup."""

    _attr_name = "Chyby zápisu"
    _attr_icon = "mdi:database-alert-outline"

    def __init__(self, entry: ConfigEntry[AtedRuntimeData]) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_write_errors"

    @property
    def native_value(self) -> int:
        return self.historian.write_errors

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"last_error": self.historian.last_error}
