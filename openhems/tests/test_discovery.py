from openhems_core.discovery import discover_devices


def test_discovery_recommends_rain_tank_level():
    states = [{"entity_id": "sensor.me202w_level_sensor_hloubka", "state": "1.2", "attributes": {"friendly_name": "Hloubka"}}]
    devices = discover_devices(states)
    rain = next(item for item in devices if item["key"] == "rain_tank")
    level = next(item for item in rain["functions"] if item["key"] == "level")
    assert level["recommended"]["entity_id"] == "sensor.me202w_level_sensor_hloubka"
