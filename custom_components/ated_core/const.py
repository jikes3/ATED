"""Constants for ATED Core."""
from __future__ import annotations

DOMAIN = "ated_core"
PLATFORMS: list[str] = ["sensor"]

CONF_SNAPSHOT_INTERVAL = "snapshot_interval"
CONF_ENTITY_IDS = "entity_ids"
CONF_EXPLANATION_DETAIL = "explanation_detail"

DEFAULT_SNAPSHOT_INTERVAL = 300
DEFAULT_EXPLANATION_DETAIL = 1
DATA_DIRECTORY = "ated_data"
SCHEMA_VERSION = 2
INTEGRATION_VERSION = "0.5.0-alpha.1"
DEVICE_REGISTRY_SCHEMA_VERSION = 1
EVENT_SCHEMA_VERSION = 1
PRESENTATION_SCHEMA_VERSION = 1
EVENT_DATA_DIRECTORY = "ated_data/events"

QUALITY_VERIFIED = "verified"
QUALITY_INVALID = "invalid"
QUALITY_MISSING = "missing"
QUALITY_VALUES = (QUALITY_VERIFIED, QUALITY_INVALID, QUALITY_MISSING)

DEFAULT_ENTITY_IDS = [
    "sensor.itepli65_temperature",
    "sensor.inverter_pool_heat_pump_venkovni_teplota",
    "sensor.me202w_level_sensor_hloubka",
    "switch.inverter_pool_heat_pump_spinac",
    "number.inverter_pool_heat_pump_teplota",
    "sensor.inverter_pool_heat_pump_teplota",
    "sensor.inverter_pool_heat_pump_teplota_prutoku",
    "sensor.inverter_pool_heat_pump_sila_kompresoru",
    "sensor.inverter_pool_heat_pump_teplota_civky",
    "sensor.inverter_pool_heat_pump_teplota_vymeniku_tepla",
]

# Rules never alter raw history. They only affect normalized_value and quality.
INVALID_RULES = {
    "sensor.inverter_pool_heat_pump_teplota": {"equals": -22.0},
}
