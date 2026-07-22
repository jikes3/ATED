"""Diagnostic sensors for ATED Core."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .models import AtedRuntimeData


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[AtedRuntimeData],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up diagnostic sensors."""
    async_add_entities(
        [
            AtedRecordsTodaySensor(entry),
            AtedLastRecordSensor(entry),
        ],
        update_before_add=True,
    )


class AtedBaseSensor(SensorEntity):
    """Base ATED diagnostic sensor."""

    _attr_has_entity_name = True
    _attr_should_poll = True

    def __init__(self, entry: ConfigEntry[AtedRuntimeData]) -> None:
        self.entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="ATED Core",
            manufacturer="ATED",
            model="Data Logger",
            sw_version="0.1.0",
        )


class AtedRecordsTodaySensor(AtedBaseSensor):
    """Number of records written since integration setup."""

    _attr_name = "Záznamy dnes"
    _attr_icon = "mdi:database-plus"

    def __init__(self, entry: ConfigEntry[AtedRuntimeData]) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_records_today"

    @property
    def native_value(self) -> int:
        return self.entry.runtime_data.logger.records_today

    @property
    def extra_state_attributes(self):
        return {
            "tracked_entities": list(self.entry.runtime_data.logger.entity_ids),
            "schema_version": 1,
        }


class AtedLastRecordSensor(AtedBaseSensor):
    """Timestamp of the latest successful write."""

    _attr_name = "Poslední záznam"
    _attr_icon = "mdi:clock-check-outline"
    _attr_device_class = "timestamp"

    def __init__(self, entry: ConfigEntry[AtedRuntimeData]) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_last_record"

    @property
    def native_value(self):
        return self.entry.runtime_data.logger.last_record_at
