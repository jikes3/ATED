"""Deterministic presentation of complete ATED explanations."""
from __future__ import annotations

from typing import Any

from .models import DetailLevel, FullExplanation, PresentedExplanation


class PresentationEngine:
    """Reveal only the amount of detail appropriate for the selected profile."""

    def __init__(self, default_level: DetailLevel = DetailLevel.BRIEF) -> None:
        self.default_level = DetailLevel.coerce(default_level)

    def present(
        self,
        explanation: FullExplanation,
        level: DetailLevel | int | str | None = None,
    ) -> PresentedExplanation:
        selected = self.default_level if level is None else DetailLevel.coerce(level)
        sections: list[dict[str, Any]] = []

        if selected >= DetailLevel.ADVANCED:
            visible_facts = [
                {
                    "code": fact.code,
                    "label": fact.label,
                    "value": fact.value,
                    "unit": fact.unit,
                }
                for fact in explanation.facts
                if selected >= fact.minimum_level
            ]
            if visible_facts:
                sections.append({"type": "facts", "items": visible_facts})

        if selected >= DetailLevel.EXPERT:
            decision = explanation.decision
            sections.append({
                "type": "decision_trace",
                "policy": explanation.policy,
                "rule": explanation.rule,
                "confidence": decision.confidence,
                "mode": decision.mode.value,
                "reasons": [
                    {"code": reason.code, "parameters": reason.parameters}
                    for reason in decision.reasons
                ],
                "blockers": [
                    {"code": blocker.code, "parameters": blocker.parameters}
                    for blocker in decision.blockers
                ],
                "alternatives": [
                    {
                        "action": item.action,
                        "score": item.score,
                        "selected": item.selected,
                        "reason_code": item.reason_code,
                    }
                    for item in explanation.alternatives
                ],
            })

        if selected >= DetailLevel.DEVELOPER:
            sections.append({
                "type": "developer",
                "decision_graph": explanation.decision_graph,
                "diagnostics": explanation.diagnostics,
            })

        summary = (
            explanation.result_text
            if selected == DetailLevel.RESULT_ONLY
            else explanation.brief_text
        )
        return PresentedExplanation(
            decision_id=explanation.decision.decision_id,
            level=selected,
            title=explanation.title,
            summary=summary,
            sections=tuple(sections),
        )
