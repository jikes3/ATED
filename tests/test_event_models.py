from datetime import datetime, timezone

import pytest

from custom_components.ated_core.event_intelligence.models import (
    ActionOrigin,
    ActionRecord,
    EventActor,
    JournalEvent,
    JournalEventType,
)


def test_event_serialization_is_versioned():
    event = JournalEvent(
        event_type=JournalEventType.ACTION,
        actor=EventActor(ActionOrigin.ATED),
        action=ActionRecord("turn_on", "switch.test", "off", "on"),
        timestamp=datetime(2026, 7, 25, tzinfo=timezone.utc),
    )
    record = event.to_record()
    assert record["schema_version"] == 1
    assert record["record_type"] == "event_journal"
    assert record["actor"]["origin"] == "ated"
    assert record["timestamp"] == "2026-07-25T00:00:00+00:00"


def test_invalid_actor_confidence_is_rejected():
    with pytest.raises(ValueError):
        EventActor(ActionOrigin.UNKNOWN, confidence=1.1)
