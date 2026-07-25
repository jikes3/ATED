"""Logical Device Registry Core for ATED."""
from __future__ import annotations

import asyncio
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass, field
from datetime import datetime
import json
import time
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from .const import DEVICE_REGISTRY_SCHEMA_VERSION

UpdateListener = Callable[[], None]


@dataclass(slots=True)
class RegisteredEntity:
    """One Home Assistant entity known to ATED."""

    entity_id: str
    domain: str
    name: str
    platform: str | None
    device_class: str | None
    unit: str | None
    available: bool
    capabilities: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RegisteredDevice:
    """Logical device assembled from one or more HA entities."""

    device_id: str
    name: str
    category: str
    manufacturer: str | None
    model: str | None
    area_id: str | None
    integration: str | None
    capabilities: list[str]
    entities: list[RegisteredEntity]


class AtedDeviceRegistry:
    """Build and persist ATED's read-only logical device inventory."""

    def __init__(
        self,
        hass: HomeAssistant,
        entity_ids: Iterable[str],
        base_path: Path,
    ) -> None:
        self.hass = hass
        self.entity_ids = tuple(dict.fromkeys(entity_ids))
        self.storage_path = base_path / "device_registry.json"

        self.devices: dict[str, RegisteredDevice] = {}
        self.missing_entities: list[str] = []
        self.unavailable_entities: list[str] = []
        self.last_refresh_at: datetime | None = None
        self.last_error: str | None = None
        self.write_errors = 0

        self._refresh_lock = asyncio.Lock()
        self._last_refresh_monotonic = 0.0
        self._listeners: set[UpdateListener] = set()

    async def async_initialize(self) -> None:
        """Create the first registry snapshot."""
        await self.async_refresh(force=True)

    def async_add_update_listener(self, listener: UpdateListener) -> Callable[[], None]:
        """Register a listener for registry changes."""
        self._listeners.add(listener)

        def remove_listener() -> None:
            self._listeners.discard(listener)

        return remove_listener

    def _notify_listeners(self) -> None:
        for listener in tuple(self._listeners):
            listener()

    async def async_refresh(self, *, force: bool = False) -> None:
        """Rebuild the logical inventory, normally at most once per five minutes."""
        now_mono = time.monotonic()
        if (
            not force
            and self._last_refresh_monotonic
            and now_mono - self._last_refresh_monotonic < 300
        ):
            return

        async with self._refresh_lock:
            now_mono = time.monotonic()
            if (
                not force
                and self._last_refresh_monotonic
                and now_mono - self._last_refresh_monotonic < 300
            ):
                return
            entity_registry = er.async_get(self.hass)
            device_registry = dr.async_get(self.hass)

            grouped: dict[str, list[RegisteredEntity]] = {}
            metadata: dict[str, dict[str, Any]] = {}
            missing: list[str] = []
            unavailable: list[str] = []

            for entity_id in self.entity_ids:
                state = self.hass.states.get(entity_id)
                registry_entry = entity_registry.async_get(entity_id)
                if state is None and registry_entry is None:
                    missing.append(entity_id)
                    continue

                domain = entity_id.split(".", 1)[0]
                available = state is not None and state.state not in ("unknown", "unavailable")
                if not available:
                    unavailable.append(entity_id)

                device_entry = None
                if registry_entry is not None and registry_entry.device_id:
                    device_entry = device_registry.async_get(registry_entry.device_id)

                logical_id = (
                    f"ha_device:{registry_entry.device_id}"
                    if registry_entry is not None and registry_entry.device_id
                    else f"entity:{entity_id}"
                )
                entity_name = _entity_name(entity_id, state, registry_entry)
                device_class = _device_class(state, registry_entry)
                unit = state.attributes.get("unit_of_measurement") if state else None
                platform = registry_entry.platform if registry_entry is not None else None
                capabilities = sorted(_infer_capabilities(domain, device_class, entity_id))

                grouped.setdefault(logical_id, []).append(
                    RegisteredEntity(
                        entity_id=entity_id,
                        domain=domain,
                        name=entity_name,
                        platform=platform,
                        device_class=device_class,
                        unit=unit,
                        available=available,
                        capabilities=capabilities,
                    )
                )

                metadata.setdefault(
                    logical_id,
                    {
                        "name": _device_name(entity_name, device_entry),
                        "manufacturer": getattr(device_entry, "manufacturer", None),
                        "model": getattr(device_entry, "model", None),
                        "area_id": getattr(device_entry, "area_id", None),
                        "integration": platform,
                    },
                )

            devices: dict[str, RegisteredDevice] = {}
            for logical_id, entities in grouped.items():
                info = metadata[logical_id]
                all_capabilities = sorted(
                    {capability for entity in entities for capability in entity.capabilities}
                )
                devices[logical_id] = RegisteredDevice(
                    device_id=logical_id,
                    name=info["name"],
                    category=_infer_category(entities),
                    manufacturer=info["manufacturer"],
                    model=info["model"],
                    area_id=info["area_id"],
                    integration=info["integration"],
                    capabilities=all_capabilities,
                    entities=sorted(entities, key=lambda item: item.entity_id),
                )

            self.devices = dict(sorted(devices.items()))
            self.missing_entities = sorted(missing)
            self.unavailable_entities = sorted(unavailable)
            self.last_refresh_at = dt_util.utcnow()

            try:
                await self.hass.async_add_executor_job(self._write_sync)
            except OSError as err:
                self.write_errors += 1
                self.last_error = f"{type(err).__name__}: {err}"
            else:
                self.last_error = None

            self._last_refresh_monotonic = time.monotonic()
            self._notify_listeners()

    @property
    def registered_device_count(self) -> int:
        return len(self.devices)

    @property
    def registered_entity_count(self) -> int:
        return sum(len(device.entities) for device in self.devices.values())

    @property
    def available_entity_count(self) -> int:
        return self.registered_entity_count - len(self.unavailable_entities)

    @property
    def available_entities(self) -> list[str]:
        """Return registered entities currently considered available."""
        unavailable = set(self.unavailable_entities)
        return sorted(
            entity.entity_id
            for device in self.devices.values()
            for entity in device.entities
            if entity.entity_id not in unavailable
        )

    @property
    def entity_diagnostics(self) -> dict[str, dict[str, Any]]:
        """Return compact per-entity diagnostics for Home Assistant attributes."""
        diagnostics: dict[str, dict[str, Any]] = {}
        for device in self.devices.values():
            for entity in device.entities:
                state = self.hass.states.get(entity.entity_id)
                diagnostics[entity.entity_id] = {
                    "device": device.name,
                    "category": device.category,
                    "available": entity.available,
                    "state": state.state if state is not None else None,
                    "unit": entity.unit,
                    "capabilities": entity.capabilities,
                }
        for entity_id in self.missing_entities:
            diagnostics[entity_id] = {
                "device": None,
                "category": None,
                "available": False,
                "state": None,
                "unit": None,
                "capabilities": [],
                "reason": "missing",
            }
        return dict(sorted(diagnostics.items()))

    @property
    def category_counts(self) -> dict[str, int]:
        return dict(sorted(Counter(device.category for device in self.devices.values()).items()))

    @property
    def capability_counts(self) -> dict[str, int]:
        counts: Counter[str] = Counter()
        for device in self.devices.values():
            counts.update(device.capabilities)
        return dict(sorted(counts.items()))

    @property
    def health(self) -> str:
        if self.last_error or self.write_errors:
            return "critical"
        if self.missing_entities:
            return "attention"
        if self.unavailable_entities:
            return "warning"
        return "healthy"

    def export(self) -> dict[str, Any]:
        """Return a serializable registry document."""
        return {
            "schema_version": DEVICE_REGISTRY_SCHEMA_VERSION,
            "generated_at": (
                self.last_refresh_at.isoformat() if self.last_refresh_at else None
            ),
            "health": self.health,
            "summary": {
                "devices": self.registered_device_count,
                "entities": self.registered_entity_count,
                "available_entities": self.available_entity_count,
                "missing_entities": len(self.missing_entities),
                "unavailable_entities": len(self.unavailable_entities),
                "categories": self.category_counts,
                "capabilities": self.capability_counts,
            },
            "available_entity_ids": self.available_entities,
            "missing_entity_ids": self.missing_entities,
            "unavailable_entity_ids": self.unavailable_entities,
            "entity_diagnostics": self.entity_diagnostics,
            "devices": [asdict(device) for device in self.devices.values()],
        }

    def _write_sync(self) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.storage_path.with_suffix(".tmp")
        with temp_path.open("w", encoding="utf-8") as handle:
            json.dump(
                self.export(),
                handle,
                ensure_ascii=False,
                indent=2,
                default=str,
            )
            handle.flush()
        temp_path.replace(self.storage_path)


def _entity_name(entity_id: str, state: Any, registry_entry: Any) -> str:
    if state is not None:
        friendly_name = state.attributes.get("friendly_name")
        if friendly_name:
            return str(friendly_name)
    if registry_entry is not None:
        return str(registry_entry.name or registry_entry.original_name or entity_id)
    return entity_id


def _device_name(entity_name: str, device_entry: Any) -> str:
    if device_entry is None:
        return entity_name
    return str(device_entry.name_by_user or device_entry.name or entity_name)


def _device_class(state: Any, registry_entry: Any) -> str | None:
    if state is not None and state.attributes.get("device_class"):
        return str(state.attributes["device_class"])
    registry_device_class = getattr(registry_entry, "device_class", None)
    if registry_device_class:
        return str(registry_device_class)
    return None


def _infer_capabilities(domain: str, device_class: str | None, entity_id: str) -> set[str]:
    capabilities: set[str] = set()
    if domain in {"sensor", "binary_sensor"}:
        capabilities.add("observe")
    if domain in {"switch", "light", "input_boolean"}:
        capabilities.update({"control", "switch"})
    if domain in {"number", "input_number"}:
        capabilities.update({"control", "setpoint"})
    if domain == "climate":
        capabilities.update({"control", "hvac", "setpoint"})

    class_map = {
        "temperature": "temperature",
        "power": "power",
        "energy": "energy",
        "battery": "battery",
        "humidity": "humidity",
        "pressure": "pressure",
        "water": "water",
        "volume": "volume",
    }
    if device_class in class_map:
        capabilities.add(class_map[device_class])

    text = entity_id.lower()
    for token, capability in (
        ("teplota", "temperature"),
        ("temperature", "temperature"),
        ("vykon", "power"),
        ("power", "power"),
        ("hloubka", "level"),
        ("level", "level"),
        ("kompresor", "compressor"),
        ("setpoint", "setpoint"),
    ):
        if token in text:
            capabilities.add(capability)
    return capabilities


def _infer_category(entities: list[RegisteredEntity]) -> str:
    text = " ".join(entity.entity_id.lower() for entity in entities)
    rules = (
        (("pool", "bazén", "bazen"), "pool"),
        (("weather", "itepli", "precipitation", "wind"), "weather"),
        (("wattrouter", "pv_", "battery", "goodwe", "inverter"), "energy"),
        (("water", "hloubka", "level_sensor", "nádrž", "nadrz"), "water"),
        (("climate", "heat_pump", "tepelne_cerpadlo"), "hvac"),
    )
    for tokens, category in rules:
        if any(token in text for token in tokens):
            return category
    return "other"
