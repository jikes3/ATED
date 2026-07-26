"""Correlate state changes with preceding decisions and actions."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from .models import ActionOrigin, EventActor, JournalEvent, JournalEventType


@dataclass(frozen=True, slots=True)
class CorrelationResult:
    actor: EventActor
    decision_id: str | None = None
    parent_event_id: str | None = None
    is_possible_rejection: bool = False


class ActionCorrelator:
    """Deterministic first-stage actor inference.

    It deliberately returns UNKNOWN when evidence is insufficient.
    """

    def __init__(
        self,
        *,
        action_window: timedelta = timedelta(seconds=15),
        rejection_window: timedelta = timedelta(seconds=30),
    ) -> None:
        self.action_window = action_window
        self.rejection_window = rejection_window
        self._recent: list[JournalEvent] = []

    def remember(self, event: JournalEvent) -> None:
        self._recent.append(event)
        cutoff = event.timestamp - max(self.action_window, self.rejection_window)
        self._recent = [item for item in self._recent if item.timestamp >= cutoff]

    def correlate_state_change(
        self,
        *,
        target_id: str,
        previous_state: object,
        new_state: object,
        timestamp: datetime,
        context_user_id: str | None = None,
    ) -> CorrelationResult:
        if context_user_id:
            return CorrelationResult(
                actor=EventActor(
                    origin=ActionOrigin.USER_HOME_ASSISTANT,
                    actor_id=context_user_id,
                    confidence=0.95,
                    evidence=("ha_context_user_id",),
                )
            )

        candidates = [
            event for event in self._recent
            if event.event_type == JournalEventType.ACTION
            and event.action is not None
            and event.action.target_id == target_id
            and timestamp - event.timestamp <= self.action_window
        ]
        if candidates:
            latest = max(candidates, key=lambda item: item.timestamp)
            return CorrelationResult(
                actor=latest.actor,
                decision_id=latest.decision_id,
                parent_event_id=latest.event_id,
            )

        opposite_ated_actions = [
            event for event in self._recent
            if event.event_type == JournalEventType.ACTION
            and event.actor.origin == ActionOrigin.ATED
            and event.action is not None
            and event.action.target_id == target_id
            and timestamp - event.timestamp <= self.rejection_window
            and event.action.state_after == previous_state
            and new_state != previous_state
        ]
        if opposite_ated_actions:
            latest = max(opposite_ated_actions, key=lambda item: item.timestamp)
            return CorrelationResult(
                actor=EventActor(
                    origin=ActionOrigin.UNKNOWN,
                    confidence=0.5,
                    evidence=("rapid_reversal_of_ated_action",),
                ),
                decision_id=latest.decision_id,
                parent_event_id=latest.event_id,
                is_possible_rejection=True,
            )

        return CorrelationResult(
            actor=EventActor(
                origin=ActionOrigin.UNKNOWN,
                confidence=0.0,
                evidence=("insufficient_evidence",),
            )
        )
