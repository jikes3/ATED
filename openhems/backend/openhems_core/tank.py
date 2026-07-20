from __future__ import annotations

import math


def horizontal_tank_volume(level_m: float, capacity_l: float, length_m: float, diameter_m: float) -> float:
    if capacity_l <= 0 or length_m <= 0 or diameter_m <= 0:
        raise ValueError("Rozměry a kapacita nádrže musí být kladné.")

    h = max(0.0, min(level_m, diameter_m))
    if h <= 0:
        return 0.0
    if h >= diameter_m:
        return capacity_l

    radius = diameter_m / 2.0
    segment_area = radius**2 * math.acos((radius - h) / radius) - (radius - h) * math.sqrt(
        max(0.0, 2 * radius * h - h**2)
    )
    full_area = math.pi * radius**2
    return capacity_l * segment_area / full_area


def refill_decision(percent: float, start: float, stop: float, emergency: float) -> str:
    if percent < emergency:
        return "NOUZOVĚ DOPLNIT"
    if percent < start:
        return "DOPLNĚNÍ DOPORUČENO"
    if percent >= stop:
        return "NEDOPLŇOVAT"
    return "SLEDOVAT"
