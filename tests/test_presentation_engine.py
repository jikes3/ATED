from custom_components.ated_core.decision.models import Decision, Reason, Blocker
from custom_components.ated_core.presentation import (
    Alternative, DetailLevel, ExplanationFact, FullExplanation, PresentationEngine,
)


def explanation():
    decision = Decision(
        action="defer_pool_heating",
        target_id="switch.pool_hp",
        reasons=(Reason("forecast_surplus", {"in_minutes": 58}),),
        blockers=(Blocker("house_load_high"),),
        confidence=0.93,
    )
    return FullExplanation(
        decision=decision,
        title="Ohřev bazénu",
        result_text="Ohřev jsem odložil.",
        brief_text="Ohřev jsem odložil kvůli očekávanému přebytku.",
        facts=(ExplanationFact("pv", "Výroba FV", 4.8, "kW"),),
        alternatives=(Alternative("defer", 0.93, True), Alternative("start_now", 0.62)),
        policy="maximize_self_consumption",
        rule="EnergySurplusRule",
        decision_graph={"node": "root"},
        diagnostics={"input_count": 12},
    )


def test_result_only_hides_sections():
    result = PresentationEngine().present(explanation(), DetailLevel.RESULT_ONLY)
    assert result.summary == "Ohřev jsem odložil."
    assert result.sections == ()


def test_advanced_shows_facts_not_trace():
    result = PresentationEngine().present(explanation(), DetailLevel.ADVANCED)
    assert [s["type"] for s in result.sections] == ["facts"]


def test_expert_shows_trace_but_not_developer_data():
    result = PresentationEngine().present(explanation(), DetailLevel.EXPERT)
    assert [s["type"] for s in result.sections] == ["facts", "decision_trace"]


def test_developer_shows_full_internal_data():
    result = PresentationEngine().present(explanation(), DetailLevel.DEVELOPER)
    assert result.sections[-1]["type"] == "developer"
