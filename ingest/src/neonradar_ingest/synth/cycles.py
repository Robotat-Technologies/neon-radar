"""Find the payment cycles the circular-flow detector would report (PHASE-1.md 5.4, M1.9b).

Mirrors the draft `circular_flow` definition with its default parameters: 2 to 6 payments
that leave an account and come back to it, strictly time-ordered, through distinct
intermediate accounts, within 14 days, with the last amount at least 0.8 times the first.
The generator uses it to keep cycles it did not plant out of the background, so that the
labels list every cycle on the fixture; tests use it to prove that.
"""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

MIN_HOPS, MAX_HOPS = 2, 6
MAX_WINDOW_SECONDS = 14 * 24 * 3600
MIN_RETURN_RATIO = (4, 5)  # last / first >= 4/5, compared in integers


@dataclass(frozen=True, slots=True)
class Hop:
    """One payment as the detector sees it: account to account, UTC seconds, amount in cents."""

    key: str
    source: str
    target: str
    ts: int
    cents: int


def find_cycles(hops: Sequence[Hop]) -> list[tuple[str, ...]]:
    """Every qualifying cycle as the keys of its payments in order, once, from its first hop."""
    outgoing: dict[str, list[Hop]] = defaultdict(list)
    for hop in sorted(hops, key=lambda h: (h.ts, h.key)):
        outgoing[hop.source].append(hop)
    found: list[tuple[str, ...]] = []

    def extend(path: list[Hop], visited: set[str]) -> None:
        first, last = path[0], path[-1]
        for hop in outgoing.get(last.target, ()):
            if hop.ts <= last.ts:
                continue
            if hop.ts - first.ts > MAX_WINDOW_SECONDS:
                break
            if hop.target == first.source:
                num, den = MIN_RETURN_RATIO
                if len(path) + 1 >= MIN_HOPS and hop.cents * den >= first.cents * num:
                    found.append(tuple(h.key for h in [*path, hop]))
            elif hop.target not in visited and len(path) + 1 < MAX_HOPS:
                extend([*path, hop], visited | {hop.target})

    for start in sorted(hops, key=lambda h: (h.ts, h.key)):
        if start.source != start.target:
            extend([start], {start.source, start.target})
    return sorted(found)
