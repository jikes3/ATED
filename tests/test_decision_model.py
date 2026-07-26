import pytest

from custom_components.ated_core.decision.models import Decision, DecisionMode


def test_alpha_decision_is_read_only():
    decision = Decision(action="hold", target_id=None, confidence=1.0)
    assert decision.mode == DecisionMode.READ_ONLY
    assert decision.executable is False


def test_live_mode_is_forbidden_in_alpha():
    with pytest.raises(ValueError):
        Decision(
            action="turn_on",
            target_id="switch.test",
            confidence=1.0,
            mode=DecisionMode.LIVE,
        )
