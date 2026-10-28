"""circular_flow 0.2.0: funds that return to the originating account, or to another account of
the same holder (PHASE-1.md 7.2 entry 4; PHASE-3.md 7.3.4).

Starts are payments of at least `min_amount`. From each start the expansion follows later
payments in the same currency, each between `min_return_ratio` and `1 + max_hop_gain` times the
first amount, within `max_window_days` of the first payment, through accounts not visited yet. A
cycle closes at the first account that is the origin (variant `same_account`) or, with
`same_holder`, another account of one of the origin's holders (variant `same_holder`), and is a
finding when it has `min_hops` to `max_hops` payments and returns at least `min_return_ratio` of
the first amount. A cycle back to the very account it left needs `min_hops_same_account` payments:
a payment straight back is the shape of a refund, a loan repaid or a cash pool sweep, and on the
development worlds a two-payment minimum added 130 alerts and no true one (50 on look-alikes, 50
on other typologies' scenarios, 30 on background activity; PHASE-3.md 7.6.5). A return to another
account of the same holder still counts from two payments. Time order makes each
cycle start at its earliest payment, so it is found once.

pattern_strength = 0.5 * return ratio + 0.3 * (1 - duration / window)
+ 0.2 * min(1, (hops - 1) / 4), clipped to [0, 1]: a heuristic for ordering the queue (PHASE-1.md
M1.9b), not a risk score.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import timedelta

from neonradar_detect.expand import FrontierItem, Path, expand
from neonradar_detect.model import Finding, Subject, clip01
from neonradar_detect.rows import Hop
from neonradar_detect.source import DetectorOutput, Source, Window

SLUG = "circular_flow"
VERSION = "0.2.0"
QUERIES = ("paid_hop.cypher", "paid_starts.cypher")
RETURN_POINT = {
    "same_account": "the originating account",
    "same_holder": "another account of the same holder",
}


@dataclass(frozen=True, slots=True)
class Params:
    min_hops: int = 2
    min_hops_same_account: int = 3
    max_hops: int = 6
    max_window_days: int = 14
    min_return_ratio: float = 0.8
    min_amount: float = 1000.0
    max_hop_gain: float = 0.05
    same_holder: bool = True
    max_starts: int = 1_000_000
    max_branching: int = 20
    max_frontier: int = 50_000


def _closes(path: Path, p: Params) -> str | None:
    """The variant if the last hop returns to the origin's side, else None."""
    origin = path.first.source
    target = path.last.target
    if target == origin:
        return "same_account"
    if p.same_holder and set(path.last.target_holders) & set(path.first.source_holders):
        return "same_holder"
    return None


def run(source: Source, p: Params, window: Window) -> DetectorOutput:
    if (
        not 2 <= p.min_hops <= p.max_hops <= 8
        or not p.min_hops <= p.min_hops_same_account <= p.max_hops
    ):
        raise ValueError("need 2 <= min_hops <= min_hops_same_account <= max_hops <= 8")
    span = timedelta(days=p.max_window_days)
    starts = source.paid_starts(p.min_amount, window.start, window.end, p.max_starts)

    def extend(path: Path, key: int) -> FrontierItem | None:
        if len(path.hops) >= p.max_hops or _closes(path, p) is not None:
            return None
        first = path.first
        return FrontierItem(
            key=key,
            account=path.last.target,
            after=path.last.ts,
            until=first.ts + span,
            min_amount=p.min_return_ratio * first.amount,
            max_amount=(1 + p.max_hop_gain) * first.amount,
            currency=first.currency,
            visited=tuple(sorted(set(path.accounts[1:]))),
        )

    def keep(path: Path, hop: Hop) -> bool:
        return True

    def accept(path: Path) -> bool:
        variant = _closes(path, p)
        if variant is None or len(path.hops) < p.min_hops:
            return False
        return variant != "same_account" or len(path.hops) >= p.min_hops_same_account

    cycles, stats = expand(
        starts,
        source.paid_hop,
        extend=extend,
        keep=keep,
        accept=accept,
        max_hops=p.max_hops,
        max_branching=p.max_branching,
        max_frontier=p.max_frontier,
    )
    findings = [f for f in (_finding(c, p) for c in cycles) if f is not None]
    return DetectorOutput(
        findings,
        {"starts": len(starts), "partial_paths": stats.partial_paths, "truncated": stats.truncated},
    )


def _finding(cycle: Path, p: Params) -> Finding | None:
    variant = _closes(cycle, p)
    first, last = cycle.first, cycle.last
    ratio = last.amount / first.amount
    if variant is None or ratio < p.min_return_ratio:
        return None
    hours = (last.ts - first.ts).total_seconds() / 3600
    window_hours = p.max_window_days * 24
    if hours > window_hours:
        return None
    hops = len(cycle.hops)
    strength = clip01(
        0.5 * min(1.0, ratio) + 0.3 * (1 - hours / window_hours) + 0.2 * min(1.0, (hops - 1) / 4)
    )
    origin = first.source
    subjects = [Subject(origin, "origin")]
    subjects += [Subject(h, "origin_holder") for h in sorted(first.source_holders)]
    if variant == "same_holder":
        subjects.append(Subject(last.target, "return_account"))
    metrics = {
        "cycle_length": hops,
        "sent_amount": round(first.amount, 2),
        "returned_amount": round(last.amount, 2),
        "currency": first.currency,
        "duration_hours": round(hours, 1),
        "duration_days": max(1, math.ceil(hours / 24)),
        "return_ratio": round(ratio, 4),
        "return_point": RETURN_POINT[variant],
    }
    return Finding(
        typology=SLUG,
        variant=variant,
        anchor=origin,
        node_ids=tuple(sorted(set(cycle.accounts))),
        edge_ids=tuple(sorted(h.edge_id for h in cycle.hops)),
        subjects=tuple(subjects),
        metrics=metrics,
        pattern_strength=strength,
        steps=tuple((h.edge_id,) for h in cycle.hops),
        window=(first.ts, last.ts),
        activity=True,
    )
