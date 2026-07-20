from __future__ import annotations

from typing import Any

DEVICE_RULES: list[dict[str, Any]] = [
    {
        "key": "rain_tank",
        "name": "Dešťová nádrž",
        "device_type": "tank",
        "icon": "💧",
        "functions": [
            {"key": "level", "name": "Hladina", "terms": ["me202w", "hloubka", "tank level", "water level"], "domains": ["sensor"]},
            {"key": "refill_pump", "name": "Dopouštěcí čerpadlo", "terms": ["tz3218_4way_switch", "dopoust", "refill pump"], "domains": ["light", "switch"]},
        ],
    },
    {
        "key": "goodwe_main",
        "name": "GoodWe hlavní měnič",
        "device_type": "inverter",
        "icon": "☀️",
        "functions": [
            {"key": "pv_power", "name": "Výkon FV", "terms": ["pv_power"], "domains": ["sensor"]},
            {"key": "pv1_power", "name": "Výkon stringu 1", "terms": ["pv1_power"], "domains": ["sensor"]},
            {"key": "pv2_power", "name": "Výkon stringu 2", "terms": ["pv2_power"], "domains": ["sensor"]},
            {"key": "battery_soc", "name": "SOC baterie", "terms": ["battery_state_of_charge"], "domains": ["sensor"]},
            {"key": "battery_power", "name": "Výkon baterie", "terms": ["battery_power"], "domains": ["sensor"]},
        ],
    },
    {
        "key": "wattrouter",
        "name": "Wattrouter",
        "device_type": "energy_router",
        "icon": "⚡",
        "functions": [
            {"key": "export_energy", "name": "Dodávka do sítě", "terms": ["wattrouter_total_forward_energy"], "domains": ["sensor"]},
            {"key": "import_energy", "name": "Odběr ze sítě", "terms": ["wattrouter_total_reverse_energy"], "domains": ["sensor"]},
        ],
    },
    {
        "key": "pool_heat_pump",
        "name": "Bazénové tepelné čerpadlo",
        "device_type": "heat_pump",
        "icon": "🏊",
        "functions": [
            {"key": "temperature", "name": "Teplota vody", "terms": ["inverter_pool_heat_pump_teplota"], "domains": ["sensor"]},
            {"key": "target_temperature", "name": "Požadovaná teplota", "terms": ["inverter_pool_heat_pump_teplota"], "domains": ["number"]},
        ],
    },
    {
        "key": "weather",
        "name": "Meteostanice",
        "device_type": "weather",
        "icon": "🌦️",
        "functions": [
            {"key": "rain_today", "name": "Srážky dnes", "terms": ["precipitation_today"], "domains": ["sensor"]},
            {"key": "rain_rate", "name": "Intenzita srážek", "terms": ["precipitation_rate", "rain_rate"], "domains": ["sensor"]},
        ],
    },
]


def entity_text(item: dict[str, Any]) -> str:
    attrs = item.get("attributes") or {}
    values = [
        item.get("entity_id", ""),
        attrs.get("friendly_name", ""),
        attrs.get("device_class", ""),
        attrs.get("unit_of_measurement", ""),
    ]
    return " ".join(str(value).lower() for value in values)


def find_matches(states: list[dict[str, Any]], terms: list[str], domains: list[str] | None = None) -> list[dict[str, Any]]:
    lowered = [term.lower() for term in terms]
    result: list[dict[str, Any]] = []
    for item in states:
        entity_id = str(item.get("entity_id", ""))
        domain = entity_id.split(".", 1)[0] if "." in entity_id else ""
        if domains and domain not in domains:
            continue
        text = entity_text(item)
        if any(term in text for term in lowered):
            result.append(item)
    return result


def _match_dict(item: dict[str, Any]) -> dict[str, Any]:
    attrs = item.get("attributes") or {}
    return {
        "entity_id": item.get("entity_id", ""),
        "name": attrs.get("friendly_name", ""),
        "state": item.get("state", ""),
        "unit": attrs.get("unit_of_measurement", ""),
    }


def discover_devices(states: list[dict[str, Any]]) -> list[dict[str, Any]]:
    discovered: list[dict[str, Any]] = []
    for rule in DEVICE_RULES:
        functions: list[dict[str, Any]] = []
        found = 0
        for function in rule["functions"]:
            matches = find_matches(states, function["terms"], function.get("domains"))
            if matches:
                found += 1
            functions.append(
                {
                    "key": function["key"],
                    "name": function["name"],
                    "count": len(matches),
                    "recommended": _match_dict(matches[0]) if matches else None,
                    "matches": [_match_dict(item) for item in matches[:30]],
                }
            )
        total = len(rule["functions"])
        status = "found" if found == total else "partial" if found else "missing"
        score = round(100 * found / total) if total else 0
        discovered.append(
            {
                "key": rule["key"],
                "name": rule["name"],
                "device_type": rule["device_type"],
                "icon": rule["icon"],
                "functions": functions,
                "status": status,
                "score": score,
            }
        )
    return discovered
