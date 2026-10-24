"""Companies House `natures_of_control` values and the statutory share bands (PHASE-2.md M2.3b).

The bands follow the statute and the API's short descriptions, not its long ones
(bulk-sources-loading.md 4.2): "more than 25% but not more than 50%" is (25, 50],
"more than 50% but less than 75%" is (50, 75), "75% or more" is [75, 100], and the overseas
entity value "more than 25%" is (25, 100].

Capacities follow the long descriptions in psc_descriptions.yml (note 4.3). For companies, LLPs
and Scottish partnerships, `-as-trust` and `-as-firm` mean that the person has significant
influence or control over a trust or firm whose trustees or members hold the right (the fifth
condition of Companies Act 2006 Schedule 1A). For registered overseas entities, `-as-trust`
means the beneficial owner is a trustee, `-as-firm` a member of a firm whose members hold the
right, and `-as-control-over-trust` and `-as-control-over-firm` control over the trust or firm.
Controlling or belonging to a trust or firm is not owning what it holds, so those values are
control of measure `trust-or-firm`, keeping the band of what the trust or firm holds. Only an
overseas entity's trustee holds the right itself ("shares (as trustee)").
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class Band:
    pct_min: float
    pct_max: float
    min_exclusive: bool
    max_exclusive: bool

    @property
    def percentage(self) -> str:
        """The FtM `percentage` text, for example "25-50"."""
        return f"{self.pct_min:g}-{self.pct_max:g}"


BANDS = {
    "25-to-50": Band(25, 50, min_exclusive=True, max_exclusive=False),
    "50-to-75": Band(50, 75, min_exclusive=True, max_exclusive=True),
    "75-to-100": Band(75, 100, min_exclusive=False, max_exclusive=False),
    "more-than-25": Band(25, 100, min_exclusive=True, max_exclusive=False),
}


@dataclass(frozen=True)
class Nature:
    value: str
    kind: str  # "ownership" or "control"
    measure: str  # shares, surplus-assets, voting, appointment, influence, nominee, trust-or-firm
    band: Band | None
    capacity: str | None  # trust, firm, control-over-trust, control-over-firm
    held: str | None  # trust-or-firm only: the right the trust or firm holds (shares, voting, ...)
    overseas: bool  # a registered overseas entity value


@dataclass(frozen=True)
class Interest:
    """One `Ownership` or `Control` record of one PSC in one company (M2.3b rule 4)."""

    kind: str
    measure: str
    capacity: str | None
    held: str | None
    band: Band | None
    values: tuple[str, ...]  # the raw natures, sorted

    @property
    def key(self) -> str:
        """The part of the record id that tells the interests of one PSC apart (PHASE-2.md 4.4):
        "shares", "voting", "shares-as-trust" (an overseas entity's trustee) or
        "trust-or-firm-shares-trust" (control over a trust whose trustees hold shares)."""
        if self.measure == "trust-or-firm":
            return f"trust-or-firm-{self.held}-{self.capacity}"
        if self.capacity:
            return f"{self.measure}-as-{self.capacity}"
        return self.measure

    @property
    def type_label(self) -> str:
        """`ownershipType` or `controlType`: "shares", "surplus assets", "shares (as trustee)",
        "voting", "appointment", "influence", "nominee" or "trust-or-firm"."""
        label = "surplus assets" if self.measure == "surplus-assets" else self.measure
        if self.measure != "trust-or-firm" and self.capacity == "trust":
            label += " (as trustee)"
        return label


_BAND = r"(?P<band>25-to-50|50-to-75|75-to-100|more-than-25)-percent"
_CAP = r"(?:-as-(?P<cap>trust|firm|control-over-trust|control-over-firm))?"
_SUFFIX = r"(?:-limited-liability-partnership|(?P<oe>-registered-overseas-entity))?"
_PATTERNS = [
    ("ownership", "shares", re.compile(rf"ownership-of-shares-{_BAND}{_CAP}{_SUFFIX}")),
    (
        "ownership",
        "surplus-assets",
        re.compile(rf"(?:part-)?right-to-share-surplus-assets-{_BAND}{_CAP}{_SUFFIX}"),
    ),
    ("control", "voting", re.compile(rf"voting-rights-{_BAND}{_CAP}{_SUFFIX}")),
    (
        "control",
        "appointment",
        re.compile(rf"right-to-appoint-and-remove-(?:directors|members|person){_CAP}{_SUFFIX}"),
    ),
    ("control", "influence", re.compile(rf"significant-influence-or-control{_CAP}{_SUFFIX}")),
    (
        "control",
        "nominee",
        re.compile(
            r"registered-owner-as-nominee-(?:person|another-entity)"
            r"-(?:england-wales|scotland|northern-ireland)(?P<oe>-registered-overseas-entity)"
        ),
    ),
]


def classify(value: str) -> Nature | None:
    """The nature of one value, or None for a value this table does not know (count it)."""
    for kind, measure, pattern in _PATTERNS:
        match = pattern.fullmatch(value)
        if match is None:
            continue
        groups = match.groupdict()
        band = BANDS[groups["band"]] if groups.get("band") else None
        capacity = groups.get("cap")
        overseas = bool(groups.get("oe"))
        if capacity is None or (overseas and capacity == "trust"):
            return Nature(value, kind, measure, band, capacity, None, overseas)
        return Nature(value, "control", "trust-or-firm", band, capacity, measure, overseas)
    return None


def combined_band(bands: Iterable[Band]) -> Band | None:
    """One band for several values of one interest: the lowest minimum and the highest maximum.

    Where two bands share a bound, the bound is closed if either is closed. Combine only the
    values of one interest (`interests` groups them): a direct holding and a trust's holding
    are different facts, and their union would describe neither.
    """
    items = list(bands)
    if not items:
        return None
    low = min(b.pct_min for b in items)
    high = max(b.pct_max for b in items)
    min_open = all(b.min_exclusive for b in items if b.pct_min == low)
    max_open = all(b.max_exclusive for b in items if b.pct_max == high)
    return Band(low, high, min_exclusive=min_open, max_exclusive=max_open)


def interests(natures: Iterable[Nature]) -> list[Interest]:
    """The interests of one PSC in one company: one per kind, measure, capacity and held right,
    each with the combined band of its values, sorted by kind and key."""
    groups: dict[tuple[str, str, str, str], list[Nature]] = {}
    for nature in natures:
        group = (nature.kind, nature.measure, nature.capacity or "", nature.held or "")
        groups.setdefault(group, []).append(nature)
    found = [
        Interest(
            kind,
            measure,
            capacity or None,
            held or None,
            combined_band(n.band for n in items if n.band is not None),
            tuple(sorted({n.value for n in items})),
        )
        for (kind, measure, capacity, held), items in groups.items()
    ]
    return sorted(found, key=lambda i: (i.kind, i.key))
