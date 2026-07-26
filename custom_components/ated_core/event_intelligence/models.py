"""Versioned event models for explainability and future learning."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

EVENT_SCHEMA_VERSION = 1


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class JournalEventType(StrEnum):
    STATE_CHANGE = "state_change"
    DECISION = "decision"
    ACTION = "action"
    USER_FEEDBACK = "user_feedback"
    AUTOMATION_PROPOSAL = "automation_proposal"


class ActionOrigin(StrEnum):
    ATED = "ated"
    USER_PHYSICAL = "user_physical"
    USER_HOME_ASSISTANT = "user_home_assistant"
    HOME_ASSISTANT_AUTOMATION = "home_assistant_automation"
    DEVICE_INTERNAL = "device_internal"
    EXTERNAL_INTEGRATION = "external_integration"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class EventActor:
    origin: ActionOrigin
    actor_id: str | None = None
    confidence: float = 1.0
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("actor confidence must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class EventContext:
    """Small context snapshot; never a full uncontrolled HA state dump."""

    house_mode: str | None = None
    area_id: str | None = None
    occupancy: bool | None = None
    illuminance_lx: float | None = None
    energy_surplus_w: float | None = None
    related_entities: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class IntentAnnotation:
    code: str
    provided_by: str
    confidence: float = 1.0
    note: str | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("intent confidence must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class ActionRecord:
    action: str
    target_id: str
    state_before: Any = None
    state_after: Any = None
    reversible: bool | None = None


@dataclass(frozen=True, slots=True)
class JournalEvent:
    event_type: JournalEventType
    actor: EventActor
    action: ActionRecord | None = None
    context: EventContext = field(default_factory=EventContext)
    decision_id: str | None = None
    explanation_codes: tuple[str, ...] = ()
    intent: IntentAnnotation | None = None
    parent_event_id: str | None = None
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=utc_now)
    schema_version: int = EVENT_SCHEMA_VERSION

    def to_record(self) -> dict[str, Any]:
        data = asdict(self)
        data["event_type"] = self.event_type.value
        data["actor"]["origin"] = self.actor.origin.value
        data["timestamp"] = self.timestamp.isoformat()
        data["record_type"] = "event_journal"
        return data
