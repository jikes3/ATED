from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class Device:
    id: int | None
    key: str
    name: str
    device_type: str
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class EntityMapping:
    id: int | None
    device_key: str
    function: str
    entity_id: str
    source: str = "manual"
    confidence: int = 100

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
