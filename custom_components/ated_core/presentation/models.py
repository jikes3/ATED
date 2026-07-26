"""Models for layered ATED explanations."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

from ..decision.models import Decision


class DetailLevel(IntEnum):
    RESULT_ONLY = 0
    BRIEF = 1
    ADVANCED = 2
    EXPERT = 3
    DEVELOPER = 4

    @classmethod
    def coerce(cls, value: int | str | "DetailLevel") -> "DetailLevel":
        if isinstance(value, cls):
            return value
        return cls(int(value))


@dataclass(frozen=True, slots=True)
class ExplanationFact:
    code: str
    label: str
    value: Any = None
    unit: str | None = None
    minimum_level: DetailLevel = DetailLevel.ADVANCED


@dataclass(frozen=True, slots=True)
class Alternative:
    action: str
    score: float | None = None
    selected: bool = False
    reason_code: str | None = None


@dataclass(frozen=True, slots=True)
class FullExplanation:
    """Canonical explanation independent of any user profile."""

    decision: Decision
    title: str
    result_text: str
    brief_text: str
    facts: tuple[ExplanationFact, ...] = ()
    alternatives: tuple[Alternative, ...] = ()
    policy: str | None = None
    rule: str | None = None
    decision_graph: dict[str, Any] = field(default_factory=dict)
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PresentedExplanation:
    decision_id: str
    level: DetailLevel
    title: str
    summary: str
    sections: tuple[dict[str, Any], ...]
