from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

OPTIONS_PATH = Path("/data/options.json")


@dataclass(frozen=True)
class Settings:
    tank_level_entity: str = "sensor.me202w_level_sensor_hloubka"
    refill_pump_entity: str = "light.tz3218_4way_switch_ts000f_svetlo_2"
    tank_capacity_l: float = 6000.0
    tank_length_m: float = 3.0
    tank_diameter_m: float = 1.6
    refill_start_percent: float = 20.0
    refill_stop_percent: float = 50.0
    emergency_percent: float = 10.0
    dry_run: bool = True


def load_settings(path: Path = OPTIONS_PATH) -> Settings:
    values: dict[str, Any] = {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            values = raw
    except (OSError, json.JSONDecodeError):
        pass

    return Settings(
        tank_level_entity=str(values.get("tank_level_entity", Settings.tank_level_entity)),
        refill_pump_entity=str(values.get("refill_pump_entity", Settings.refill_pump_entity)),
        tank_capacity_l=float(values.get("tank_capacity_l", Settings.tank_capacity_l)),
        tank_length_m=float(values.get("tank_length_m", Settings.tank_length_m)),
        tank_diameter_m=float(values.get("tank_diameter_m", Settings.tank_diameter_m)),
        refill_start_percent=float(values.get("refill_start_percent", Settings.refill_start_percent)),
        refill_stop_percent=float(values.get("refill_stop_percent", Settings.refill_stop_percent)),
        emergency_percent=float(values.get("emergency_percent", Settings.emergency_percent)),
        dry_run=bool(values.get("dry_run", Settings.dry_run)),
    )
