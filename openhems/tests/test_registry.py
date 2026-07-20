from pathlib import Path

import pytest

from openhems_core.registry import Device, EntityMapping, RegistryStore


def test_registry_roundtrip(tmp_path: Path) -> None:
    store = RegistryStore(tmp_path / "registry.db")
    store.init()
    store.upsert_device(Device(None, "rain_tank", "Dešťová nádrž", "tank"))
    saved = store.upsert_mapping(
        EntityMapping(None, "rain_tank", "level", "sensor.tank_level", "test", 99)
    )
    assert saved.entity_id == "sensor.tank_level"
    devices = store.list_devices()
    assert devices[0]["mappings"][0]["function"] == "level"


def test_mapping_requires_existing_device(tmp_path: Path) -> None:
    store = RegistryStore(tmp_path / "registry.db")
    store.init()
    with pytest.raises(ValueError):
        store.upsert_mapping(EntityMapping(None, "missing", "power", "sensor.power"))
