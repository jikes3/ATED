"""Runtime models for ATED Core."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .device_registry import AtedDeviceRegistry
from .event_intelligence import ActionCorrelator, EventJournal
from .logger import AtedHistorian
from .presentation import PresentationEngine


@dataclass(slots=True)
class AtedRuntimeData:
    """Runtime data stored on the config entry."""

    historian: AtedHistorian
    device_registry: AtedDeviceRegistry
    event_journal: EventJournal
    action_correlator: ActionCorrelator
    presentation_engine: PresentationEngine
    unsub_state: Callable[[], None]
    unsub_snapshot: Callable[[], None]
    unsub_started: Callable[[], None] | None = None
