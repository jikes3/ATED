from datetime import datetime, timedelta, timezone

from custom_components.ated_core.event_intelligence.correlation import ActionCorrelator
from custom_components.ated_core.event_intelligence.models import (
    ActionOrigin,
    ActionRecord,
    EventActor,
    JournalEvent,
    JournalEventType,
)


def test_ated_action_is_correlated_with_state_change():
    now = datetime(2026, 7, 25, 20, 0, tzinfo=timezone.utc)
    action = JournalEvent(
        event_type=JournalEventType.ACTION,
        actor=EventActor(ActionOrigin.ATED),
        action=ActionRecord("turn_on", "light.kitchen", "off", "on"),
        decision_id="decision-1",
        timestamp=now,
    )
    correlator = ActionCorrelator()
    correlator.remember(action)
    result = correlator.correlate_state_change(
        target_id="light.kitchen",
        previous_state="off",
        new_state="on",
        timestamp=now + timedelta(seconds=2),
    )
    assert result.actor.origin == ActionOrigin.ATED
    assert result.decision_id == "decision-1"


def test_rapid_reversal_can_be_marked_as_possible_rejection():
    now = datetime(2026, 7, 25, 20, 0, tzinfo=timezone.utc)
    action = JournalEvent(
        event_type=JournalEventType.ACTION,
        actor=EventActor(ActionOrigin.ATED),
        action=ActionRecord("turn_off", "light.kitchen", "on", "off"),
        decision_id="decision-2",
        timestamp=now,
    )
    correlator = ActionCorrelator(action_window=timedelta(seconds=1))
    correlator.remember(action)
    result = correlator.correlate_state_change(
        target_id="light.kitchen",
        previous_state="off",
        new_state="on",
        timestamp=now + timedelta(seconds=5),
    )
    assert result.is_possible_rejection is True
    assert result.parent_event_id == action.event_id
