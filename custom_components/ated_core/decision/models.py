"""Minimal read-only Decision model linked to Event Journal."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4


class DecisionMode(StrEnum):
    READ_ONLY = "read_only"
    DRY_RUN = "dry_run"
    LIVE = "live"


@dataclass(frozen=True, slots=True)
class Reason:
    code: str
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Blocker:
    code: str
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Decision:
    action: str
    target_id: str | None
    reasons: tuple[Reason, ...] = ()
    blockers: tuple[Blocker, ...] = ()
    confidence: float = 0.0
    mode: DecisionMode = DecisionMode.READ_ONLY
    decision_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("decision confidence must be between 0 and 1")
        if self.mode is DecisionMode.LIVE:
            raise ValueError("ATED 0.5.0-alpha.1 must not create live decisions")

    @property
    def executable(self) -> bool:
        return self.mode is DecisionMode.LIVE and not self.blockers
