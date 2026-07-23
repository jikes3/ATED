"""Runtime models for ATED Core."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .logger import AtedHistorian


@dataclass(slots=True)
class AtedRuntimeData:
    """Runtime data stored on the config entry."""

    historian: AtedHistorian
    unsub_state: Callable[[], None]
    unsub_snapshot: Callable[[], None]
