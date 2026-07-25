"""Diagnostic sensors for ATED Core."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfInformation, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN, INTEGRATION_VERSION, QUALITY_VERIFIED, SCHEMA_VERSION
from .health import HistorianHealthMonitor
from .models import AtedRuntimeData

VERSION = INTEGRATION_VERSION
_MONITORS: dict[str, HistorianHealthMonitor] = {}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[AtedRuntimeData],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Historian Health Core sensors."""
    historian = entry.runtime_data.historian
    base_path = Path(
        getattr(historian, "base_path", hass.config.path("ated_data"))
    )

    monitor = HistorianHealthMonitor(hass, base_path)
    _MONITORS[entry.entry_id] = monitor
    await monitor.async_refresh(force=True)

    async_add_entities(
        [
            AtedHistorianStatusSensor(entry, monitor),
            AtedWriteErrorsSensor(entry, monitor),
            AtedDataQualitySensor(entry, monitor),
            AtedLastSnapshotSensor(entry, monitor),
            AtedLastRecordSensor(entry, monitor),
            AtedTrackedEntitiesSensor(entry, monitor),
            AtedArchiveSizeSensor(entry, monitor),
            AtedRecordsTodaySensor(entry, monitor),
            AtedTotalRecordsSensor(entry, monitor),
            AtedArchiveDaysSensor(entry, monitor),
            AtedFirstRecordSensor(entry, monitor),
            AtedDailyGrowthSensor(entry, monitor),
            AtedHistorianUptimeSensor(entry, monitor),
            AtedDiskFreeSensor(entry, monitor),
            AtedDiskUsageSensor(entry, monitor),
            AtedStorageEstimateSensor(entry, monitor),
            AtedHistorianHealthSensor(entry, monitor),
            AtedVersionSensor(entry, monitor),
            AtedDeviceRegistryHealthSensor(entry, monitor),
            AtedRegisteredDevicesSensor(entry, monitor),
            AtedRegisteredEntitiesSensor(entry, monitor),
            AtedUnavailableEntitiesSensor(entry, monitor),
            AtedMissingEntitiesSensor(entry, monitor),
        ],
        update_before_add=False,
    )


class AtedBaseSensor(SensorEntity):
    """Base ATED diagnostic sensor."""

    _attr_has_entity_name = True
    _attr_should_poll = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        entry: ConfigEntry[AtedRuntimeData],
        monitor: HistorianHealthMonitor,
    ) -> None:
        self.entry = entry
        self.monitor = monitor
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="ATED Core",
            manufacturer="ATED",
            model=f"Historian Health Core • ATED {VERSION}",
        )

    @property
    def historian(self):
        """Return the active historian instance."""
        return self.entry.runtime_data.historian

    async def async_update(self) -> None:
        """Refresh cached health information."""
        await self.monitor.async_refresh()


class AtedHistorianStatusSensor(AtedBaseSensor):
    _attr_name = "Historian stav"
    _attr_icon = "mdi:database-check"

    def __init__(self, entry, monitor):
        super().__init__(entry, monitor)
        self._attr_unique_id = f"{entry.entry_id}_historian_status"

    @property
    def native_value(self) -> str:
        if getattr(self.historian, "last_error", None):
            return "error"
        if getattr(self.historian, "last_record_at", None) is None:
            return "starting"
        return "online"


class AtedWriteErrorsSensor(AtedBaseSensor):
    _attr_name = "Chyby zápisu"
    _attr_icon = "mdi:database-alert"

    def __init__(self, entry, monitor):
        super().__init__(entry, monitor)
        self._attr_unique_id = f"{entry.entry_id}_write_errors"

    @property
    def native_value(self) -> int:
        return int(getattr(self.historian, "write_errors", 0) or 0)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"poslední_chyba": getattr(self.historian, "last_error", None)}


class AtedDataQualitySensor(AtedBaseSensor):
    _attr_name = "Kvalita dat"
    _attr_icon = "mdi:shield-check"
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, entry, monitor):
        super().__init__(entry, monitor)
        self._attr_unique_id = f"{entry.entry_id}_data_quality"

    @property
    def native_value(self) -> int:
        counts = dict(getattr(self.historian, "quality_counts", {}) or {})
        total = sum(int(value or 0) for value in counts.values())
        if total <= 0:
            return 0
        verified = int(counts.get(QUALITY_VERIFIED, 0) or 0)
        return round((verified / total) * 100)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "souhrn_kvality": dict(
                getattr(self.historian, "quality_counts", {}) or {}
            )
        }


class AtedLastSnapshotSensor(AtedBaseSensor):
    _attr_name = "Poslední snapshot"
    _attr_icon = "mdi:timer-sand"
    _attr_device_class = "timestamp"

    def __init__(self, entry, monitor):
        super().__init__(entry, monitor)
        self._attr_unique_id = f"{entry.entry_id}_last_snapshot"

    @property
    def native_value(self):
        return (
            getattr(self.historian, "last_snapshot_at", None)
            or self.monitor.snapshot.last_snapshot_at
        )


class AtedLastRecordSensor(AtedBaseSensor):
    _attr_name = "Poslední záznam"
    _attr_icon = "mdi:clock-check-outline"
    _attr_device_class = "timestamp"

    def __init__(self, entry, monitor):
        super().__init__(entry, monitor)
        self._attr_unique_id = f"{entry.entry_id}_last_record"

    @property
    def native_value(self):
        return (
            getattr(self.historian, "last_record_at", None)
            or self.monitor.snapshot.last_record_at
        )


class AtedTrackedEntitiesSensor(AtedBaseSensor):
    _attr_name = "Sledované entity"
    _attr_icon = "mdi:format-list-checks"

    def __init__(self, entry, monitor):
        super().__init__(entry, monitor)
        self._attr_unique_id = f"{entry.entry_id}_tracked_entities"

    @property
    def native_value(self) -> int:
        return len(tuple(getattr(self.historian, "entity_ids", ())))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"entities": list(getattr(self.historian, "entity_ids", ()))}


class AtedArchiveSizeSensor(AtedBaseSensor):
    _attr_name = "Velikost archivu"
    _attr_icon = "mdi:database"
    _attr_native_unit_of_measurement = UnitOfInformation.MEBIBYTES

    def __init__(self, entry, monitor):
        super().__init__(entry, monitor)
        self._attr_unique_id = f"{entry.entry_id}_archive_size"

    @property
    def native_value(self) -> float:
        return round(self.monitor.snapshot.archive_size_bytes / 1024**2, 3)


class AtedRecordsTodaySensor(AtedBaseSensor):
    _attr_name = "Záznamy dnes"
    _attr_icon = "mdi:database-plus"

    def __init__(self, entry, monitor):
        super().__init__(entry, monitor)
        self._attr_unique_id = f"{entry.entry_id}_records_today"

    @property
    def native_value(self) -> int:
        return int(getattr(self.historian, "records_today", 0) or 0)


class AtedTotalRecordsSensor(AtedBaseSensor):
    _attr_name = "Záznamů celkem"
    _attr_icon = "mdi:counter"

    def __init__(self, entry, monitor):
        super().__init__(entry, monitor)
        self._attr_unique_id = f"{entry.entry_id}_total_records"

    @property
    def native_value(self) -> int:
        return self.monitor.snapshot.total_records

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"nečitelné_řádky": self.monitor.snapshot.unreadable_lines}


class AtedArchiveDaysSensor(AtedBaseSensor):
    _attr_name = "Dnů v archivu"
    _attr_icon = "mdi:calendar-range"

    def __init__(self, entry, monitor):
        super().__init__(entry, monitor)
        self._attr_unique_id = f"{entry.entry_id}_archive_days"

    @property
    def native_value(self) -> int:
        return self.monitor.snapshot.archive_days


class AtedFirstRecordSensor(AtedBaseSensor):
    _attr_name = "První záznam"
    _attr_icon = "mdi:calendar-start"
    _attr_device_class = "timestamp"

    def __init__(self, entry, monitor):
        super().__init__(entry, monitor)
        self._attr_unique_id = f"{entry.entry_id}_first_record"

    @property
    def native_value(self):
        return self.monitor.snapshot.first_record_at


class AtedDailyGrowthSensor(AtedBaseSensor):
    _attr_name = "Průměrný růst archivu"
    _attr_icon = "mdi:chart-line"
    _attr_native_unit_of_measurement = "MiB/den"

    def __init__(self, entry, monitor):
        super().__init__(entry, monitor)
        self._attr_unique_id = f"{entry.entry_id}_daily_growth"

    @property
    def native_value(self) -> float:
        return round(self.monitor.snapshot.daily_growth_bytes / 1024**2, 3)


class AtedHistorianUptimeSensor(AtedBaseSensor):
    _attr_name = "Doba běhu Historianu"
    _attr_icon = "mdi:timer-outline"
    _attr_native_unit_of_measurement = UnitOfTime.HOURS

    def __init__(self, entry, monitor):
        super().__init__(entry, monitor)
        self._attr_unique_id = f"{entry.entry_id}_historian_uptime"

    @property
    def native_value(self) -> float:
        return round(self.monitor.uptime_seconds / 3600, 1)


class AtedDiskFreeSensor(AtedBaseSensor):
    _attr_name = "Volné místo"
    _attr_icon = "mdi:harddisk"
    _attr_native_unit_of_measurement = UnitOfInformation.GIGABYTES

    def __init__(self, entry, monitor):
        super().__init__(entry, monitor)
        self._attr_unique_id = f"{entry.entry_id}_disk_free"

    @property
    def native_value(self) -> float:
        return round(self.monitor.snapshot.disk_free_bytes / 1000**3, 2)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        snap = self.monitor.snapshot
        return {
            "celková_kapacita_GB": round(snap.disk_total_bytes / 1000**3, 2),
            "využito_GB": round(snap.disk_used_bytes / 1000**3, 2),
            "sledovaná_cesta": str(self.monitor.base_path),
        }


class AtedDiskUsageSensor(AtedBaseSensor):
    _attr_name = "Využití disku"
    _attr_icon = "mdi:chart-donut"
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, entry, monitor):
        super().__init__(entry, monitor)
        self._attr_unique_id = f"{entry.entry_id}_disk_usage"

    @property
    def native_value(self) -> float:
        return self.monitor.snapshot.disk_used_percent


class AtedStorageEstimateSensor(AtedBaseSensor):
    _attr_name = "Odhad zbývající kapacity"
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, entry, monitor):
        super().__init__(entry, monitor)
        self._attr_unique_id = f"{entry.entry_id}_storage_estimate"

    @property
    def native_value(self) -> str:
        days = self.monitor.snapshot.estimated_days_remaining
        if days is None:
            return "nelze určit"

        years = days / 365.25
        if years >= 100:
            return "> 100 let"
        if years >= 2:
            return f"{years:.0f} let"
        if years >= 1:
            return f"{years:.1f} roku"
        return f"{days:.0f} dnů"


class AtedHistorianHealthSensor(AtedBaseSensor):
    _attr_name = "Historian Health"
    _attr_icon = "mdi:heart-pulse"

    def __init__(self, entry, monitor):
        super().__init__(entry, monitor)
        self._attr_unique_id = f"{entry.entry_id}_historian_health"

    @property
    def native_value(self) -> str:
        snap = self.monitor.snapshot
        errors = int(getattr(self.historian, "write_errors", 0) or 0)
        free_gb = snap.disk_free_bytes / 1000**3

        if errors > 0 or snap.unreadable_lines > 0 or free_gb < 2:
            return "critical"
        if snap.disk_used_percent >= 90:
            return "warning"
        if snap.disk_used_percent >= 80:
            return "attention"
        return "healthy"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        snap = self.monitor.snapshot
        return {
            "verze": VERSION,
            "schema": SCHEMA_VERSION,
            "obnoveno": snap.refreshed_at.isoformat(),
            "nečitelné_řádky": snap.unreadable_lines,
            "hranice_varování_procent": 80,
            "hranice_kritická_procent": 90,
            "kritické_volné_místo_GB": 2,
        }


class AtedVersionSensor(AtedBaseSensor):
    _attr_name = "Verze ATED"
    _attr_icon = "mdi:tag-outline"

    def __init__(self, entry, monitor):
        super().__init__(entry, monitor)
        self._attr_unique_id = f"{entry.entry_id}_ated_version"

    @property
    def native_value(self) -> str:
        return VERSION


class AtedDeviceRegistryBaseSensor(AtedBaseSensor):
    """Base sensor for Device Registry Core."""

    @property
    def registry(self):
        return self.entry.runtime_data.device_registry

    async def async_update(self) -> None:
        await self.registry.async_refresh()

    def __init__(self, entry, monitor):
        super().__init__(entry, monitor)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_device_registry")},
            name="ATED Device Registry",
            manufacturer="ATED",
            model=f"Device Registry Core • ATED {VERSION}",
            via_device=(DOMAIN, entry.entry_id),
        )


class AtedDeviceRegistryHealthSensor(AtedDeviceRegistryBaseSensor):
    _attr_name = "Device Registry Health"
    _attr_icon = "mdi:devices"

    def __init__(self, entry, monitor):
        super().__init__(entry, monitor)
        self._attr_unique_id = f"{entry.entry_id}_device_registry_health"

    @property
    def native_value(self) -> str:
        return self.registry.health

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "obnoveno": (
                self.registry.last_refresh_at.isoformat()
                if self.registry.last_refresh_at
                else None
            ),
            "poslední_chyba": self.registry.last_error,
            "chyby_zápisu": self.registry.write_errors,
            "soubor_registru": str(self.registry.storage_path),
            "kategorie": self.registry.category_counts,
            "capabilities": self.registry.capability_counts,
        }


class AtedRegisteredDevicesSensor(AtedDeviceRegistryBaseSensor):
    _attr_name = "Registrovaná zařízení"
    _attr_icon = "mdi:devices"

    def __init__(self, entry, monitor):
        super().__init__(entry, monitor)
        self._attr_unique_id = f"{entry.entry_id}_registered_devices"

    @property
    def native_value(self) -> int:
        return self.registry.registered_device_count

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "zařízení": [
                {
                    "id": device.device_id,
                    "název": device.name,
                    "kategorie": device.category,
                    "integrace": device.integration,
                    "capabilities": device.capabilities,
                    "počet_entit": len(device.entities),
                }
                for device in self.registry.devices.values()
            ]
        }


class AtedRegisteredEntitiesSensor(AtedDeviceRegistryBaseSensor):
    _attr_name = "Registrované entity"
    _attr_icon = "mdi:format-list-checks"

    def __init__(self, entry, monitor):
        super().__init__(entry, monitor)
        self._attr_unique_id = f"{entry.entry_id}_registered_entities"

    @property
    def native_value(self) -> int:
        return self.registry.registered_entity_count

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "dostupné": self.registry.available_entity_count,
            "sledované": list(self.registry.entity_ids),
        }


class AtedUnavailableEntitiesSensor(AtedDeviceRegistryBaseSensor):
    _attr_name = "Nedostupné entity"
    _attr_icon = "mdi:cloud-alert"

    def __init__(self, entry, monitor):
        super().__init__(entry, monitor)
        self._attr_unique_id = f"{entry.entry_id}_unavailable_entities"

    @property
    def native_value(self) -> int:
        return len(self.registry.unavailable_entities)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"entities": self.registry.unavailable_entities}


class AtedMissingEntitiesSensor(AtedDeviceRegistryBaseSensor):
    _attr_name = "Chybějící entity"
    _attr_icon = "mdi:link-variant-off"

    def __init__(self, entry, monitor):
        super().__init__(entry, monitor)
        self._attr_unique_id = f"{entry.entry_id}_missing_entities"

    @property
    def native_value(self) -> int:
        return len(self.registry.missing_entities)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"entities": self.registry.missing_entities}
