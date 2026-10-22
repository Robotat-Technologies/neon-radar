"""What a detector returns before it becomes a C4 alert (PHASE-3.md 7.1.1).

A `Finding` holds ids, metrics and the order of the explanation steps, never text: the alert builder
renders the text from the typology's templates (`wording.py`), so every sentence passes the
wording lint in one place.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class Subject:
    entity_id: str
    role: str


@dataclass(frozen=True, slots=True)
class Finding:
    typology: str
    variant: str
    anchor: str
    node_ids: tuple[str, ...]
    edge_ids: tuple[str, ...]
    subjects: tuple[Subject, ...]
    metrics: Mapping[str, Any]
    pattern_strength: float
    steps: tuple[tuple[str, ...], ...]
    window: tuple[datetime, datetime] | None = None
    activity: bool = False
    extra: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if list(self.node_ids) != sorted(set(self.node_ids)):
            raise ValueError("node_ids must be sorted and unique")
        if list(self.edge_ids) != sorted(set(self.edge_ids)):
            raise ValueError("edge_ids must be sorted and unique")
        if not 0.0 <= self.pattern_strength <= 1.0:
            raise ValueError("pattern_strength must lie in [0, 1]")
        edges = set(self.edge_ids)
        if any(e not in edges for step in self.steps for e in step):
            raise ValueError("every step edge must be an evidence edge")
        if self.anchor not in set(self.node_ids):
            raise ValueError("the anchor must be an evidence node")
        if not self.subjects:
            raise ValueError("a finding needs at least one subject")


@dataclass(frozen=True, slots=True)
class NodeInfo:
    """What the alert builder and the policy need to know about one node."""

    id: str
    labels: frozenset[str]
    caption: str
    synthetic: bool
    datasets: tuple[str, ...]
    holders: tuple[str, ...] = ()


def clip01(value: float) -> float:
    """Clip to [0, 1] and round to 4 decimals, the form every pattern strength takes."""
    return round(min(1.0, max(0.0, value)), 4)


@dataclass(frozen=True, slots=True)
class EdgeInfo:
    """What the alert builder and the policy need to know about one evidence relationship."""

    id: str
    type: str
    source: str
    target: str
    synthetic: bool
    amount: float | None = None
    currency: str = ""
    ts: datetime | None = None
    channel: str = ""
    share_min: float | None = None
    share_max: float | None = None
    share_min_exclusive: bool = False
    share_max_exclusive: bool = False
    role: str = ""
    control_type: str = ""
    start_date: str = ""
    end_date: str = ""
